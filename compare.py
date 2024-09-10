import os
import filecmp
from difflib import unified_diff
import git
import shutil

def clone_repo(repo_url, target_dir):
    """
    Clone a repository from a given URL to a target directory.
    If the directory already exists, it will be removed and re-cloned.
    """
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    git.Repo.clone_from(repo_url, target_dir)
    print(f"Cloned {repo_url} to {target_dir}")

def compare_dirs(dir1, dir2):
    """
    Compare two directories recursively and return differences.
    """
    comp = filecmp.dircmp(dir1, dir2)
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

def print_file_diff(file1, file2):
    """
    Print unified diff of two files.
    """
    try:
        with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
            diff = unified_diff(
                f1.readlines(),
                f2.readlines(),
                fromfile=file1,
                tofile=file2,
            )
            for line in diff:
                print(line.rstrip())
    except UnicodeDecodeError:
        print(f"Unable to compare {file1} and {file2} due to encoding issues.")

def main(repo1_url, repo2_url):
    # Create data directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    # Clone repositories
    repo1_name = repo1_url.split('/')[-1]
    repo2_name = repo2_url.split('/')[-1]
    repo1_path = os.path.join(data_dir, repo1_name)
    repo2_path = os.path.join(data_dir, repo2_name)

    clone_repo(repo1_url, repo1_path)
    clone_repo(repo2_url, repo2_path)

    # Compare repositories
    diff_files, only_in_repo1, only_in_repo2 = compare_dirs(repo1_path, repo2_path)
    
    print("\nFiles that differ:")
    for file in diff_files:
        print(f"  {file}")
        file1 = os.path.join(repo1_path, file)
        file2 = os.path.join(repo2_path, file)
        print_file_diff(file1, file2)
        print("\n")
    
    print("Files/directories only in first repository:")
    for item in only_in_repo1:
        print(f"  {item}")
    
    print("\nFiles/directories only in second repository:")
    for item in only_in_repo2:
        print(f"  {item}")

if __name__ == "__main__":
    repo1_url = "https://github.com/reserve-protocol/protocol"
    repo2_url = "https://github.com/code-423n4/2024-07-reserve"
    main(repo1_url, repo2_url)