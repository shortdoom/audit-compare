import os
import filecmp
from difflib import HtmlDiff, unified_diff
import git
import shutil
import datetime
import logging
from jinja2 import Template
import argparse
import sys

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

def clone_repo(repo_url, target_dir):
    """Clone a repository from a given URL to a target directory."""
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    try:
        git.Repo.clone_from(repo_url, target_dir)
        logging.info(f"Cloned {repo_url} to {target_dir}")
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

def get_file_extensions(files):
    """Get unique file extensions from the list of files."""
    return sorted(set(os.path.splitext(file[0])[1] for file in files if os.path.splitext(file[0])[1]))

def get_directories(files):
    """Get unique directories from the list of files."""
    return sorted(set(os.path.dirname(file[0]) for file in files if os.path.dirname(file[0])))

def generate_html_report(repo1_name, repo2_name, diff_files, same_files, only_in_repo1, only_in_repo2, repo1_path, repo2_path):
    """Generate a single HTML report containing all diffs, similarities, and file lists."""
    extensions = get_file_extensions(diff_files + same_files)
    directories = get_directories(diff_files + same_files)
    
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
            #jump-table { margin-bottom: 20px; }
            #jump-table table { border-collapse: collapse; width: 100%; }
            #jump-table th, #jump-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            #jump-table th { background-color: #f2f2f2; }
            #filter-section { margin-bottom: 20px; }
            .hidden { display: none; }
            .filter-options { margin-top: 10px; }
            .filter-options span { margin-right: 10px; cursor: pointer; }
            .filter-options span:hover { text-decoration: underline; }
            .same-files { margin-bottom: 20px; }
            .same-files table { border-collapse: collapse; width: 100%; }
            .same-files th, .same-files td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .same-files th { background-color: #f2f2f2; }
            #search-bar { margin-bottom: 20px; }
            #search-input { width: 300px; padding: 5px; }
            .section-header { cursor: pointer; background-color: #f0f0f0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; }
            .section-header:hover { background-color: #e0e0e0; }
            .section-content { display: none; }
        </style>
    </head>
    <body>
        <h1>Repository Comparison: {{ repo1_name }} vs {{ repo2_name }}</h1>
        
        <div id="filter-section">
            <label for="file-filter">Filter files: </label>
            <input type="text" id="file-filter" placeholder="e.g., .sol, contracts/">
            <button onclick="filterFiles()">Filter</button>
            <button onclick="resetFilter()">Reset</button>
            <div class="filter-options">
                <strong>Extensions:</strong>
                {% for ext in extensions %}
                <span onclick="setFilter('{{ ext }}')">{{ ext }}</span>
                {% endfor %}
            </div>
            <div class="filter-options">
                <strong>Directories:</strong>
                {% for dir in directories %}
                <span onclick="setFilter('{{ dir }}/')">{{ dir }}/</span>
                {% endfor %}
            </div>
        </div>
        
        <div id="search-bar">
            <input type="text" id="search-input" placeholder="Search for files...">
            <button onclick="searchFiles()">Search</button>
        </div>

        <div id="jump-table" class="section">
            <h2 class="section-header" onclick="toggleSection('jump-table-content')">Jump to File Differences: ({{ diff_files|length }})</h2>
            <div id="jump-table-content" class="section-content">
                <table>
                    <tr>
                        <th>File in {{ repo1_name }}</th>
                        <th>File in {{ repo2_name }}</th>
                        <th>Extension</th>
                    </tr>
                    {% for file1, file2 in diff_files %}
                    <tr class="jump-row" data-file="{{ file1 }}">
                        <td><a href="#{{ file1 | replace('/', '-') }}">{{ file1 }}</a></td>
                        <td>{{ file2 }}</td>
                        <td>{{ file1.split('.')[-1] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        
        <div class="same-files section">
            <h2 class="section-header" onclick="toggleSection('same-files-content')">Files with Same Content: ({{ same_files|length }})</h2>
            <div id="same-files-content" class="section-content">
                <table>
                    <tr>
                        <th>File in {{ repo1_name }}</th>
                        <th>File in {{ repo2_name }}</th>
                    </tr>
                    {% for file1, file2 in same_files %}
                    <tr>
                        <td>{{ file1 }}</td>
                        <td>{{ file2 }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        
        <div class="file-list section">
            <h2 class="section-header" onclick="toggleSection('only-in-repo1-content')">Files only in {{ repo1_name }}: ({{ only_in_repo1|length }})</h2>
            <div id="only-in-repo1-content" class="section-content">
                <ul>
                {% for file in only_in_repo1 %}
                    <li>{{ file }}</li>
                {% endfor %}
                </ul>
            </div>
        </div>
        
        <div class="file-list section">
            <h2 class="section-header" onclick="toggleSection('only-in-repo2-content')">Files only in {{ repo2_name }}: ({{ only_in_repo2|length }})</h2>
            <div id="only-in-repo2-content" class="section-content">
                <ul>
                {% for file in only_in_repo2 %}
                    <li>{{ file }}</li>
                {% endfor %}
                </ul>
            </div>
        </div>
        
        <div class="diff-section section">
            <h2 class="section-header" onclick="toggleSection('diff-section-content')">File Differences: ({{ diff_files|length }})</h2>
            <div id="diff-section-content" class="section-content">
                {% for file1, file2 in diff_files %}
                <div id="{{ file1 | replace('/', '-') }}" class="diff-file" data-file="{{ file1 }}">
                    <h3>{{ file1 }} vs {{ file2 }}</h3>
                    {{ side_by_side_diff(repo1_path + '/' + file1, repo2_path + '/' + file2, repo1_name + '/' + file1, repo2_name + '/' + file2) }}
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            function toggleSection(sectionId) {
                var content = document.getElementById(sectionId);
                var header = content.previousElementSibling;
                if (content.style.display === 'none' || content.style.display === '') {
                    content.style.display = 'block';
                    header.innerHTML = header.innerHTML.replace('▼', '▲');
                } else {
                    content.style.display = 'none';
                    header.innerHTML = header.innerHTML.replace('▲', '▼');
                }
            }

            function filterFiles() {
                const filterValue = document.getElementById('file-filter').value.toLowerCase();
                const diffFiles = document.querySelectorAll('.diff-file');
                const jumpRows = document.querySelectorAll('.jump-row');

                diffFiles.forEach(file => {
                    const fileName = file.getAttribute('data-file').toLowerCase();
                    if (fileName.includes(filterValue)) {
                        file.classList.remove('hidden');
                    } else {
                        file.classList.add('hidden');
                    }
                });

                jumpRows.forEach(row => {
                    const fileName = row.getAttribute('data-file').toLowerCase();
                    if (fileName.includes(filterValue)) {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                });
            }

            function resetFilter() {
                document.getElementById('file-filter').value = '';
                const diffFiles = document.querySelectorAll('.diff-file');
                const jumpRows = document.querySelectorAll('.jump-row');

                diffFiles.forEach(file => file.classList.remove('hidden'));
                jumpRows.forEach(row => row.classList.remove('hidden'));
            }

            function setFilter(value) {
                document.getElementById('file-filter').value = value;
                filterFiles();
            }
            
            function searchFiles() {
                var searchValue = document.getElementById('search-input').value.toLowerCase();
                var jumpTable = document.getElementById('jump-table-content');
                var sameFiles = document.getElementById('same-files-content');
                var onlyInRepo1 = document.getElementById('only-in-repo1-content');
                var onlyInRepo2 = document.getElementById('only-in-repo2-content');
                var diffSection = document.getElementById('diff-section-content');

                // Search in jump table
                var jumpRows = jumpTable.getElementsByClassName('jump-row');
                var visibleJumpRows = 0;
                for (var i = 0; i < jumpRows.length; i++) {
                    var fileName = jumpRows[i].getAttribute('data-file').toLowerCase();
                    if (fileName.includes(searchValue)) {
                        jumpRows[i].style.display = '';
                        visibleJumpRows++;
                    } else {
                        jumpRows[i].style.display = 'none';
                    }
                }
                jumpTable.style.display = visibleJumpRows > 0 ? 'block' : 'none';

                // Search in same files
                var sameFileRows = sameFiles.getElementsByTagName('tr');
                var visibleSameFiles = 0;
                for (var i = 1; i < sameFileRows.length; i++) { // Start from 1 to skip header
                    var cells = sameFileRows[i].getElementsByTagName('td');
                    if (cells[0].textContent.toLowerCase().includes(searchValue) || 
                        cells[1].textContent.toLowerCase().includes(searchValue)) {
                        sameFileRows[i].style.display = '';
                        visibleSameFiles++;
                    } else {
                        sameFileRows[i].style.display = 'none';
                    }
                }
                sameFiles.style.display = visibleSameFiles > 0 ? 'block' : 'none';

                // Search in files only in repo1
                var repo1Items = onlyInRepo1.getElementsByTagName('li');
                var visibleRepo1Items = 0;
                for (var i = 0; i < repo1Items.length; i++) {
                    if (repo1Items[i].textContent.toLowerCase().includes(searchValue)) {
                        repo1Items[i].style.display = '';
                        visibleRepo1Items++;
                    } else {
                        repo1Items[i].style.display = 'none';
                    }
                }
                onlyInRepo1.style.display = visibleRepo1Items > 0 ? 'block' : 'none';

                // Search in files only in repo2
                var repo2Items = onlyInRepo2.getElementsByTagName('li');
                var visibleRepo2Items = 0;
                for (var i = 0; i < repo2Items.length; i++) {
                    if (repo2Items[i].textContent.toLowerCase().includes(searchValue)) {
                        repo2Items[i].style.display = '';
                        visibleRepo2Items++;
                    } else {
                        repo2Items[i].style.display = 'none';
                    }
                }
                onlyInRepo2.style.display = visibleRepo2Items > 0 ? 'block' : 'none';

                // Search in diff files
                var diffFiles = diffSection.getElementsByClassName('diff-file');
                var visibleDiffFiles = 0;
                for (var i = 0; i < diffFiles.length; i++) {
                    var fileName = diffFiles[i].getAttribute('data-file').toLowerCase();
                    if (fileName.includes(searchValue)) {
                        diffFiles[i].style.display = '';
                        visibleDiffFiles++;
                    } else {
                        diffFiles[i].style.display = 'none';
                    }
                }
                diffSection.style.display = visibleDiffFiles > 0 ? 'block' : 'none';
            }

            // Initialize all sections as closed and add click events
            document.addEventListener('DOMContentLoaded', function() {
                var sections = document.getElementsByClassName('section');
                for (var i = 0; i < sections.length; i++) {
                    var header = sections[i].getElementsByClassName('section-header')[0];
                    var content = sections[i].getElementsByClassName('section-content')[0];
                    content.style.display = 'none';
                    header.innerHTML += ' ▼';
                    header.style.cursor = 'pointer';
                    header.style.backgroundColor = '#f0f0f0';
                    header.style.padding = '10px';
                    header.style.border = '1px solid #ddd';
                    header.style.borderRadius = '5px';
                    header.style.marginBottom = '10px';
                    header.onclick = function() {
                        toggleSection(this.nextElementSibling.id);
                    };
                }
            });
        </script>
    </body>
    </html>
    """
    
    template = Template(html_template)
    html_content = template.render(
        repo1_name=repo1_name,
        repo2_name=repo2_name,
        diff_files=diff_files,
        same_files=same_files,
        only_in_repo1=only_in_repo1,
        only_in_repo2=only_in_repo2,
        repo1_path=repo1_path,
        repo2_path=repo2_path,
        side_by_side_diff=side_by_side_diff,
        extensions=extensions,
        directories=directories
    )
    
    return html_content

def get_full_repo_name(repo_url):
    """Extract the full repository name (owner/repo) from the URL."""
    parts = repo_url.rstrip('/').split('/')
    return f"{parts[-2]}_{parts[-1]}"

def main(repo1_url, repo2_url, deep_compare=False):
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Script started at {start_time}")
    logging.info(f"Comparing repositories: {repo1_url} and {repo2_url}")
    logging.info(f"Deep compare: {deep_compare}")

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

    clone_repo(repo1_url, repo1_path)
    clone_repo(repo2_url, repo2_path)

    diff_files, same_files, only_in_repo1, only_in_repo2 = compare_dirs(repo1_path, repo2_path, deep_compare)
    
    logging.info(f"Number of files only in {repo1_full_name}: {len(only_in_repo1)}")
    logging.info(f"Number of files only in {repo2_full_name}: {len(only_in_repo2)}")
    logging.info(f"Number of different files: {len(diff_files)}")
    logging.info(f"Number of files with same content: {len(same_files)}")
    
    html_report = generate_html_report(repo1_full_name, repo2_full_name, diff_files, same_files, only_in_repo1, only_in_repo2, repo1_path, repo2_path)
    
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
    args = parser.parse_args()

    if args.repo1 and args.repo2:
        repo1_url = args.repo1
        repo2_url = args.repo2
    else:
        repo1_url = input("Enter the URL of the first repository: ")
        repo2_url = input("Enter the URL of the second repository: ")

    main(repo1_url, repo2_url, args.deep)