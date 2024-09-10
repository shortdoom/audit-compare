import os
import filecmp
from difflib import HtmlDiff
import git
import shutil
import datetime
import logging
from itertools import zip_longest

def setup_logging():
    """Set up logging to file with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"repo_comparison_{timestamp}.log"
    logging.basicConfig(filename=log_filename, level=logging.INFO, 
                        format='%(message)s')
    return log_filename

def clone_repo(repo_url, target_dir):
    """Clone a repository from a given URL to a target directory."""
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    git.Repo.clone_from(repo_url, target_dir)
    logging.info(f"Cloned {repo_url} to {target_dir}")

def compare_dirs(dir1, dir2):
    """Compare two directories recursively and return differences."""
    diff_files = []
    only_in_dir1 = []
    only_in_dir2 = []
    
    for root, _, files in os.walk(dir1):
        for file in files:
            path1 = os.path.join(root, file)
            path2 = os.path.join(dir2, os.path.relpath(path1, dir1))
            if os.path.exists(path2):
                if not filecmp.cmp(path1, path2, shallow=False):
                    diff_files.append(os.path.relpath(path1, dir1))
            else:
                only_in_dir1.append(os.path.relpath(path1, dir1))
    
    for root, _, files in os.walk(dir2):
        for file in files:
            path2 = os.path.join(root, file)
            path1 = os.path.join(dir1, os.path.relpath(path2, dir2))
            if not os.path.exists(path1):
                only_in_dir2.append(os.path.relpath(path2, dir2))

    return diff_files, only_in_dir1, only_in_dir2

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
            
            return diff_table
    except UnicodeDecodeError:
        return f"Unable to compare {file1} and {file2} due to encoding issues."

def main(repo1_url, repo2_url):
    log_filename = setup_logging()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    repo1_name = repo1_url.split('/')[-1]
    repo2_name = repo2_url.split('/')[-1]
    repo1_path = os.path.join(data_dir, repo1_name)
    repo2_path = os.path.join(data_dir, repo2_name)

    clone_repo(repo1_url, repo1_path)
    clone_repo(repo2_url, repo2_path)

    diff_files, only_in_repo1, only_in_repo2 = compare_dirs(repo1_path, repo2_path)
    
    logging.info("\nFiles that differ:")
    for file in diff_files:
        logging.info(f"  {file}")
        file1 = os.path.join(repo1_path, file)
        file2 = os.path.join(repo2_path, file)
        diff_html = side_by_side_diff(file1, file2, f"{repo1_name}/{file}", f"{repo2_name}/{file}")
        
        # Save diff HTML to a separate file
        diff_filename = f"diff_{file.replace('/', '_')}.html"
        with open(diff_filename, 'w', encoding='utf-8') as diff_file:
            diff_file.write(diff_html)
        logging.info(f"  Diff saved to {diff_filename}")
    
    logging.info("\nFiles/directories only in first repository:")
    for item in only_in_repo1:
        logging.info(f"  {item}")
    
    logging.info("\nFiles/directories only in second repository:")
    for item in only_in_repo2:
        logging.info(f"  {item}")
    
    print(f"Comparison complete. Results saved to {log_filename}")
    print("Diff files have been saved as separate HTML files.")

if __name__ == "__main__":
    repo1_url = "https://github.com/reserve-protocol/protocol"
    repo2_url = "https://github.com/code-423n4/2024-07-reserve"
    main(repo1_url, repo2_url)