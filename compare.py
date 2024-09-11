import os
import filecmp
from difflib import HtmlDiff, unified_diff
import git
import shutil
import datetime
import logging
import argparse
import sys
from report_template import generate_html_report

# Set up global logging
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, 'script.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

def setup_logging(log_dir):
    """Set up logging to file with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"repo_comparison_{timestamp}.log")
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(file_formatter)
    logging.getLogger().addHandler(file_handler)
    return log_filename

def clone_repo(repo_url, target_dir, depth=1):
    """Clone a repository from a given URL to a target directory."""
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    try:
        if depth is None:
            git.Repo.clone_from(repo_url, target_dir)
            logging.info(f"Cloned {repo_url} to {target_dir} (full clone)")
        else:
            git.Repo.clone_from(repo_url, target_dir, depth=depth)
            logging.info(f"Cloned {repo_url} to {target_dir} (depth: {depth})")
    except git.exc.GitCommandError as e:
        logging.error(f"Failed to clone {repo_url}: {str(e)}")
        raise

def compare_dirs(dir1, dir2, deep_compare=False):
    """Compare two directories and return differences."""
    diff_files = []
    same_files = []
    only_in_dir1 = []
    only_in_dir2 = []
    
    if deep_compare:
        matching_files = find_matching_files(dir1, dir2)
        
        for file1_path, file2_path in matching_files:
            if not filecmp.cmp(file1_path, file2_path, shallow=False):
                diff_files.append((os.path.relpath(file1_path, dir1), os.path.relpath(file2_path, dir2)))
        
        # Deep scan (thorough comparison)
        for root, _, files in os.walk(dir1):
            if '.git' in root.split(os.path.sep):
                continue
            for file in files:
                path1 = os.path.join(root, file)
                path2 = os.path.join(dir2, os.path.relpath(path1, dir1))
                if os.path.exists(path2):
                    if not filecmp.cmp(path1, path2, shallow=False):
                        diff_files.append((os.path.relpath(path1, dir1), os.path.relpath(path2, dir2)))
                    else:
                        same_files.append((os.path.relpath(path1, dir1), os.path.relpath(path2, dir2)))
                else:
                    only_in_dir1.append(os.path.relpath(path1, dir1))
        
        for root, _, files in os.walk(dir2):
            if '.git' in root.split(os.path.sep):
                continue
            for file in files:
                path2 = os.path.join(root, file)
                path1 = os.path.join(dir1, os.path.relpath(path2, dir2))
                if not os.path.exists(path1):
                    only_in_dir2.append(os.path.relpath(path2, dir2))
    else:
        # Shallow scan (original behavior from compare_old.py)
        for root, _, files in os.walk(dir1):
            if '.git' in root.split(os.path.sep):
                continue
            for file in files:
                path1 = os.path.join(root, file)
                path2 = os.path.join(dir2, os.path.relpath(path1, dir1))
                if os.path.exists(path2):
                    if not filecmp.cmp(path1, path2, shallow=False):
                        diff_files.append((os.path.relpath(path1, dir1), os.path.relpath(path2, dir2)))
                    else:
                        same_files.append((os.path.relpath(path1, dir1), os.path.relpath(path2, dir2)))
                else:
                    only_in_dir1.append(os.path.relpath(path1, dir1))
        
        for root, _, files in os.walk(dir2):
            if '.git' in root.split(os.path.sep):
                continue
            for file in files:
                path2 = os.path.join(root, file)
                path1 = os.path.join(dir1, os.path.relpath(path2, dir2))
                if not os.path.exists(path1):
                    only_in_dir2.append(os.path.relpath(path2, dir2))

    return diff_files, same_files, only_in_dir1, only_in_dir2

def find_matching_files(dir1, dir2):
    """Find files with the same name across different directory structures."""
    # NOTE: This is a simple heuristic to find files with the same name across different directory structures.
    # NOTE: A smarter approach would be to use a more advanced algorithm to find files with the "similar" content.
    matching_files = []
    for root1, _, files1 in os.walk(dir1):
        if '.git' in root1.split(os.path.sep):
            continue
        for file1 in files1:
            file1_path = os.path.join(root1, file1)
            for root2, _, files2 in os.walk(dir2):
                if '.git' in root2.split(os.path.sep):
                    continue
                if file1 in files2:
                    file2_path = os.path.join(root2, file1)
                    matching_files.append((file1_path, file2_path))
    return matching_files

def side_by_side_diff(file1, file2, file1_name, file2_name):
    """Generate a side-by-side diff of two files."""
    try:
        with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            
            differ = HtmlDiff()
            diff_table = differ.make_table(
                lines1, lines2, file1_name, file2_name, context=True, numlines=3
            )
            
            # Generate unified diff for logging
            unified = '\n'.join(unified_diff(lines1, lines2, file1_name, file2_name))
            logging.debug(f"Diff between {file1_name} and {file2_name}:\n{unified}\n")
            
            return diff_table
    except UnicodeDecodeError:
        error_message = f"Unable to compare {file1} and {file2} due to encoding issues."
        logging.debug(error_message)
        return f"<p>{error_message}</p>"

def get_full_repo_name(repo_url):
    """Extract the full repository name (owner/repo) from the URL."""
    parts = repo_url.rstrip('/').split('/')
    return f"{parts[-2]}_{parts[-1]}"

def main(repo1_url, repo2_url, deep_compare=False, depth=1):
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Script started at {start_time}")
    logging.info(f"Comparing repositories: {repo1_url} and {repo2_url}")
    logging.info(f"Deep compare: {deep_compare}")
    logging.info(f"Clone depth: {depth if depth is not None else 'Full'}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    repo1_full_name = get_full_repo_name(repo1_url)
    repo2_full_name = get_full_repo_name(repo2_url)
    comparison_dir = os.path.join(data_dir, f"compare_{repo1_full_name}_to_{repo2_full_name}")
    os.makedirs(comparison_dir, exist_ok=True)

    log_filename = setup_logging(comparison_dir)

    repo1_path = os.path.join(data_dir, repo1_full_name)
    repo2_path = os.path.join(data_dir, repo2_full_name)

    clone_repo(repo1_url, repo1_path, depth)
    clone_repo(repo2_url, repo2_path, depth)

    diff_files, same_files, only_in_repo1, only_in_repo2 = compare_dirs(repo1_path, repo2_path, deep_compare)
    
    logging.info(f"Number of files only in {repo1_full_name}: {len(only_in_repo1)}")
    logging.info(f"Number of files only in {repo2_full_name}: {len(only_in_repo2)}")
    logging.info(f"Number of different files: {len(diff_files)}")
    logging.info(f"Number of files with same content: {len(same_files)}")
    
    # Write the full diff dump to the repo_comparison log file
    with open(log_filename, 'a', encoding='utf-8') as log_file:
        log_file.write("\n\n" + "=" * 50 + "\n")
        log_file.write("FULL DIFF DUMP:\n\n")
        for file1, file2 in diff_files:
            try:
                with open(os.path.join(repo1_path, file1), 'r', encoding='utf-8') as f1, \
                     open(os.path.join(repo2_path, file2), 'r', encoding='utf-8') as f2:
                    lines1 = f1.readlines()
                    lines2 = f2.readlines()
                    diff = ''.join(unified_diff(lines1, lines2, 
                                                fromfile=f"{repo1_full_name}/{file1}", 
                                                tofile=f"{repo2_full_name}/{file2}"))
                    log_file.write(f"Diff between {file1} and {file2}:\n{diff}\n\n")
            except UnicodeDecodeError:
                log_file.write(f"Unable to compare {file1} and {file2} due to encoding issues.\n\n")
    
    html_report = generate_html_report(
        repo1_full_name, 
        repo2_full_name, 
        diff_files, 
        same_files, 
        only_in_repo1, 
        only_in_repo2, 
        repo1_path, 
        repo2_path,
        side_by_side_diff
    )
    
    report_filename = os.path.join(comparison_dir, "comparison_report.html")
    with open(report_filename, 'w', encoding='utf-8') as report_file:
        report_file.write(html_report)
    
    logging.info(f"Comparison complete. Results saved to {log_filename}")
    logging.info(f"HTML report saved to {report_filename}")
    
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Script ended at {end_time}")
    logging.info("=" * 50)  # Add a separator between runs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two GitHub repositories")
    parser.add_argument("--repo1", help="URL of the first repository")
    parser.add_argument("--repo2", help="URL of the second repository")
    parser.add_argument("--deep", action="store_true", help="Perform deep comparison")
    parser.add_argument("--depth", type=int, default=1, help="Depth of git clone (default: 1, use None for full clone)")
    args = parser.parse_args()

    if args.repo1 and args.repo2:
        repo1_url = args.repo1
        repo2_url = args.repo2
    else:
        repo1_url = input("Enter the URL of the first repository: ")
        repo2_url = input("Enter the URL of the second repository: ")

    depth = args.depth if args.depth > 0 else None
    main(repo1_url, repo2_url, args.deep, depth)