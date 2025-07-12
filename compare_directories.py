#!/usr/bin/env python3
"""compare_directories.py

A standalone CLI utility to compare two local directories. It re-uses the
core comparison and reporting helpers already implemented in `compare.py`
(`compare_dirs`, `side_by_side_diff`, `setup_logging`) and the HTML report
template in `report_template.py`.

Example
-------
$ python compare_directories.py /path/to/dirA /path/to/dirB --deep

This will write logs under `data/compare_dirA_to_dirB/` and generate an
HTML report named `comparison_report.html` in the same folder.
"""

import os
import datetime
import argparse
import logging
from pathlib import Path

# Re-use helpers from the existing repo comparison script
from compare import compare_dirs, side_by_side_diff, setup_logging  # type: ignore
from report_template import generate_html_report


def _safe_name(path: str) -> str:
    """Return a filesystem-safe name derived from *path* for use in output dirs."""
    # Use the last component of the path; fall back to the whole path with path
    # separators replaced if the basename is empty (e.g. when comparing '/')
    base = os.path.basename(os.path.normpath(path))
    return base if base else path.strip(os.sep).replace(os.sep, "_")


def main(dir1: str, dir2: str, deep_compare: bool = False) -> None:
    """Run a comparison between *dir1* and *dir2*.

    Parameters
    ----------
    dir1, dir2: str
        Absolute or relative paths of the directories to compare.
    deep_compare: bool
        If *True*, perform an exhaustive comparison that attempts to match files
        with identical names across different folder structures before doing a
        standard directory walk. Mirrors the `--deep` option of *compare.py*.
    """
    # Resolve to absolute paths for clarity in logs and report links
    dir1_path = os.path.abspath(dir1)
    dir2_path = os.path.abspath(dir2)

    if not os.path.isdir(dir1_path):
        raise NotADirectoryError(f"{dir1_path} is not a valid directory")
    if not os.path.isdir(dir2_path):
        raise NotADirectoryError(f"{dir2_path} is not a valid directory")

    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Directory compare started at {start_time}")
    logging.info(f"Comparing directories: {dir1_path} vs {dir2_path}")
    logging.info(f"Deep compare: {deep_compare}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    dir1_name = _safe_name(dir1_path)
    dir2_name = _safe_name(dir2_path)
    comparison_dir = os.path.join(data_dir, f"compare_{dir1_name}_to_{dir2_name}")
    os.makedirs(comparison_dir, exist_ok=True)

    # Set up file-specific logging inside the comparison directory
    log_filename = setup_logging(comparison_dir)

    # Perform the directory comparison
    (
        diff_files,
        same_files,
        only_in_dir1,
        only_in_dir2,
    ) = compare_dirs(dir1_path, dir2_path, deep_compare)

    logging.info(f"Number of files only in {dir1_name}: {len(only_in_dir1)}")
    logging.info(f"Number of files only in {dir2_name}: {len(only_in_dir2)}")
    logging.info(f"Number of different files: {len(diff_files)}")
    logging.info(f"Number of files with same content: {len(same_files)}")

    # Append full diff dump to the comparison-specific log file
    with open(log_filename, "a", encoding="utf-8") as log_file:
        log_file.write("\n\n" + "=" * 50 + "\n")
        log_file.write("FULL DIFF DUMP:\n\n")
        for file1, file2 in diff_files:
            try:
                with open(os.path.join(dir1_path, file1), "r", encoding="utf-8") as f1, open(
                    os.path.join(dir2_path, file2), "r", encoding="utf-8"
                ) as f2:
                    from difflib import unified_diff

                    lines1 = f1.readlines()
                    lines2 = f2.readlines()
                    diff = "".join(
                        unified_diff(
                            lines1,
                            lines2,
                            fromfile=f"{dir1_name}/{file1}",
                            tofile=f"{dir2_name}/{file2}",
                        )
                    )
                    log_file.write(f"Diff between {file1} and {file2}:\n{diff}\n\n")
            except UnicodeDecodeError:
                log_file.write(
                    f"Unable to compare {file1} and {file2} due to encoding issues.\n\n"
                )

    # Generate the HTML report
    html_report = generate_html_report(
        dir1_name,
        dir2_name,
        diff_files,
        same_files,
        only_in_dir1,
        only_in_dir2,
        dir1_path,
        dir2_path,
        side_by_side_diff,
    )

    report_filename = os.path.join(comparison_dir, "comparison_report.html")
    with open(report_filename, "w", encoding="utf-8") as report_file:
        report_file.write(html_report)

    logging.info(f"Comparison complete. Results saved to {log_filename}")
    logging.info(f"HTML report saved to {report_filename}")

    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Directory compare ended at {end_time}")
    logging.info("=" * 50)  # Separator between runs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two local directories")
    parser.add_argument("dir1", help="Path to the first directory")
    parser.add_argument("dir2", help="Path to the second directory")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Perform a deep comparison (attempt to match identical-named files across disparate folder structures)",
    )
    args = parser.parse_args()

    main(args.dir1, args.dir2, args.deep) 