from jinja2 import Template
import os

def get_file_extensions(files):
    """Get unique file extensions from the list of files."""
    return sorted(set(os.path.splitext(file[0])[1] for file in files if os.path.splitext(file[0])[1]))

def get_directories(files):
    """Get unique directories from the list of files."""
    return sorted(set(os.path.dirname(file[0]) for file in files if os.path.dirname(file[0])))

def generate_html_report(repo1_name, repo2_name, diff_files, same_files, only_in_repo1, only_in_repo2, repo1_path, repo2_path, side_by_side_diff):
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
            <label for="search-input">Search files: </label>
            <input type="text" id="search-input" placeholder="e.g., Contract.sol, contracts/">
            <button onclick="searchFiles()">Search</button>
            <button onclick="resetSearch()">Reset</button>
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
                let hasVisibleContent = false;

                diffFiles.forEach(file => {
                    const fileName = file.getAttribute('data-file').toLowerCase();
                    if (fileName.includes(filterValue)) {
                        file.classList.remove('hidden');
                        hasVisibleContent = true;
                    } else {
                        file.classList.add('hidden');
                    }
                });

                jumpRows.forEach(row => {
                    const fileName = row.getAttribute('data-file').toLowerCase();
                    if (fileName.includes(filterValue)) {
                        row.classList.remove('hidden');
                        hasVisibleContent = true;
                    } else {
                        row.classList.add('hidden');
                    }
                });

                // Unfold sections if there's visible content
                if (hasVisibleContent) {
                    document.querySelectorAll('.section-content').forEach(section => {
                        section.style.display = 'block';
                        const header = section.previousElementSibling;
                        header.innerHTML = header.innerHTML.replace('▼', '▲');
                    });
                }
            }

            function resetFilter() {
                document.getElementById('file-filter').value = '';
                const diffFiles = document.querySelectorAll('.diff-file');
                const jumpRows = document.querySelectorAll('.jump-row');

                diffFiles.forEach(file => file.classList.remove('hidden'));
                jumpRows.forEach(row => row.classList.remove('hidden'));

                // Fold all sections
                document.querySelectorAll('.section-content').forEach(section => {
                    section.style.display = 'none';
                    const header = section.previousElementSibling;
                    header.innerHTML = header.innerHTML.replace('▲', '▼');
                });
            }

            function setFilter(value) {
                document.getElementById('file-filter').value = value;
                filterFiles();
            }
            
            function searchFiles() {
                var searchValue = document.getElementById('search-input').value.toLowerCase();
                var sections = document.getElementsByClassName('section-content');

                for (var i = 0; i < sections.length; i++) {
                    var section = sections[i];
                    var rows = section.getElementsByTagName('tr');
                    var items = section.getElementsByTagName('li');
                    var visibleCount = 0;

                    // Search in table rows
                    for (var j = 0; j < rows.length; j++) {
                        var row = rows[j];
                        if (row.textContent.toLowerCase().includes(searchValue)) {
                            row.style.display = '';
                            visibleCount++;
                        } else {
                            row.style.display = 'none';
                        }
                    }

                    // Search in list items
                    for (var k = 0; k < items.length; k++) {
                        var item = items[k];
                        if (item.textContent.toLowerCase().includes(searchValue)) {
                            item.style.display = '';
                            visibleCount++;
                        } else {
                            item.style.display = 'none';
                        }
                    }

                    // Show/hide section based on search results
                    section.style.display = visibleCount > 0 ? 'block' : 'none';
                    var header = section.previousElementSibling;
                    header.innerHTML = header.innerHTML.replace(visibleCount > 0 ? '▼' : '▲', visibleCount > 0 ? '▲' : '▼');
                }

                // Always show headers
                var headers = document.getElementsByClassName('section-header');
                for (var l = 0; l < headers.length; l++) {
                    headers[l].style.display = 'block';
                }
            }

            function resetSearch() {
                document.getElementById('search-input').value = '';
                var sections = document.getElementsByClassName('section-content');

                for (var i = 0; i < sections.length; i++) {
                    var section = sections[i];
                    var rows = section.getElementsByTagName('tr');
                    var items = section.getElementsByTagName('li');

                    // Reset table rows
                    for (var j = 0; j < rows.length; j++) {
                        rows[j].style.display = '';
                    }

                    // Reset list items
                    for (var k = 0; k < items.length; k++) {
                        items[k].style.display = '';
                    }

                    // Hide sections
                    section.style.display = 'none';
                    var header = section.previousElementSibling;
                    header.innerHTML = header.innerHTML.replace('▲', '▼');
                }
            }

            // Initialize all sections as closed
            document.addEventListener('DOMContentLoaded', function() {
                var sections = document.getElementsByClassName('section');
                for (var i = 0; i < sections.length; i++) {
                    var header = sections[i].getElementsByClassName('section-header')[0];
                    var content = sections[i].getElementsByClassName('section-content')[0];
                    content.style.display = 'none';
                    header.innerHTML += ' ▼';
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
