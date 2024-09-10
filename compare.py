import os
import filecmp
from difflib import HtmlDiff
import git
import shutil
import datetime
import logging
from jinja2 import Template

def setup_logging(log_dir):
    """Set up logging to file with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"repo_comparison_{timestamp}.log")
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
        return f"<p>Unable to compare {file1} and {file2} due to encoding issues.</p>"

def generate_html_report(repo1_name, repo2_name, diff_files, only_in_repo1, only_in_repo2, repo1_path, repo2_path):
    """Generate a single HTML report containing all diffs and file lists."""
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Repository Comparison: {{ repo1_name }} vs {{ repo2_name }}</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
            h1, h2 { color: #333; }
            .file-list { margin-bottom: 20px; }
            .file-list ul { list-style-type: none; padding-left: 20px; }
            .diff-section { margin-bottom: 40px; }
            .diff-file { margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; }
            .diff-file h3 { margin-top: 0; }
            table.diff { font-family: monospace; border-collapse: collapse; width: 100%; }
            .diff_header { background-color: #e0e0e0; }
            td.diff_header { text-align: right; }
            .diff_next { background-color: #c0c0c0; }
            .diff_add { background-color: #aaffaa; }
            .diff_chg { background-color: #ffff77; }
            .diff_sub { background-color: #ffaaaa; }
        </style>
    </head>
    <body>
        <h1>Repository Comparison: {{ repo1_name }} vs {{ repo2_name }}</h1>
        
        <div class="file-list">
            <h2>Files only in {{ repo1_name }}:</h2>
            <ul>
            {% for file in only_in_repo1 %}
                <li>{{ file }}</li>
            {% endfor %}
            </ul>
        </div>
        
        <div class="file-list">
            <h2>Files only in {{ repo2_name }}:</h2>
            <ul>
            {% for file in only_in_repo2 %}
                <li>{{ file }}</li>
            {% endfor %}
            </ul>
        </div>
        
        <div class="diff-section">
            <h2>File Differences:</h2>
            {% for file in diff_files %}
            <div class="diff-file">
                <h3>{{ file }}</h3>
                {{ side_by_side_diff(repo1_path + '/' + file, repo2_path + '/' + file, repo1_name + '/' + file, repo2_name + '/' + file) }}
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    template = Template(html_template)
    html_content = template.render(
        repo1_name=repo1_name,
        repo2_name=repo2_name,
        diff_files=diff_files,
        only_in_repo1=only_in_repo1,
        only_in_repo2=only_in_repo2,
        repo1_path=repo1_path,
        repo2_path=repo2_path,
        side_by_side_diff=side_by_side_diff
    )
    
    return html_content

def main(repo1_url, repo2_url):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    repo1_name = repo1_url.split('/')[-1]
    repo2_name = repo2_url.split('/')[-1]
    comparison_dir = os.path.join(data_dir, f"compare_{repo1_name}_to_{repo2_name}")
    os.makedirs(comparison_dir, exist_ok=True)

    log_filename = setup_logging(comparison_dir)

    repo1_path = os.path.join(data_dir, repo1_name)
    repo2_path = os.path.join(data_dir, repo2_name)

    clone_repo(repo1_url, repo1_path)
    clone_repo(repo2_url, repo2_path)

    diff_files, only_in_repo1, only_in_repo2 = compare_dirs(repo1_path, repo2_path)
    
    html_report = generate_html_report(repo1_name, repo2_name, diff_files, only_in_repo1, only_in_repo2, repo1_path, repo2_path)
    
    report_filename = os.path.join(comparison_dir, "comparison_report.html")
    with open(report_filename, 'w', encoding='utf-8') as report_file:
        report_file.write(html_report)
    
    logging.info(f"Comparison complete. Results saved to {log_filename}")
    logging.info(f"HTML report saved to {report_filename}")
    
    print(f"Comparison complete. Results saved to {log_filename}")
    print(f"HTML report saved to {report_filename}")

if __name__ == "__main__":
    repo1_url = "https://github.com/reserve-protocol/protocol"
    repo2_url = "https://github.com/code-423n4/2024-07-reserve"
    main(repo1_url, repo2_url)