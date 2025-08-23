"""File pattern matching utilities for command-line tools."""

import glob
import sys
from pathlib import Path


def convert_pattern_to_test_and_code_patterns(pattern):
    """Convert a file pattern to both test and code file patterns.

    Args:
        pattern: A file pattern (can be code file, test file, with/without extensions)

    Returns:
        tuple: (test_pattern, code_pattern)
    """
    if pattern.startswith("test_"):
        # Already a test file pattern
        test_pattern = pattern
        # Also create the corresponding code file pattern
        code_pattern = pattern[5:]  # Remove 'test_' prefix
    else:
        # Convert code file to test file pattern
        if pattern.endswith(".py"):
            base_name = pattern[:-3]
            test_pattern = f"test_{base_name}"
            code_pattern = base_name
        else:
            test_pattern = f"test_{pattern}"
            code_pattern = pattern

    return test_pattern, code_pattern


def match_pattern_against_files(
    pattern, all_files, include_tests=True, include_code=True
):
    """Match a single file pattern against a list of files.

    Args:
        pattern: File pattern to match
        all_files: List of all files to search in
        include_tests: Whether to include test files in results
        include_code: Whether to include code files in results

    Returns:
        list: Matching file paths
    """
    filtered_files = []

    # If pattern doesn't contain path separators, search in file names
    if "/" not in pattern and "\\" not in pattern:
        test_pattern, code_pattern = convert_pattern_to_test_and_code_patterns(pattern)

        # Match files containing the pattern in their name
        for file_path in all_files:
            file_name = Path(file_path).name

            # Match test files
            if include_tests and (
                test_pattern in file_name
                or test_pattern + ".py" in file_name
                or (test_pattern.endswith(".py") and test_pattern[:-3] in file_name)
            ):
                filtered_files.append(file_path)
            # Match code files
            elif include_code and (
                code_pattern in file_name
                or code_pattern + ".py" in file_name
                or (code_pattern.endswith(".py") and code_pattern[:-3] in file_name)
            ):
                filtered_files.append(file_path)
    else:
        # Use glob pattern matching for full paths
        matching_files = glob.glob(pattern, recursive=True)
        # Only include files that are also in our all_files list
        filtered_files.extend([f for f in matching_files if f in all_files])

    return filtered_files


def filter_files_by_patterns(
    all_files,
    file_patterns,
    include_tests=True,
    include_code=True,
    error_message_prefix="files",
):
    """Filter files based on provided patterns.

    Args:
        all_files: List of all files to filter from
        file_patterns: List of file patterns to match
        include_tests: Whether to include test files in results
        include_code: Whether to include code files in results
        error_message_prefix: Prefix for error messages

    Returns:
        list: Filtered file paths
    """
    filtered_files = []

    for pattern in file_patterns:
        pattern_matches = match_pattern_against_files(
            pattern, all_files, include_tests, include_code
        )
        filtered_files.extend(pattern_matches)

    if not filtered_files:
        print(f"No {error_message_prefix} found matching patterns: {file_patterns}")
        sys.exit(1)

    return list(set(filtered_files))  # Remove duplicates


def get_all_project_files(include_tests=True, include_code=True):
    """Get all Python files in the project."""
    all_files = []

    if include_code:
        code_files = glob.glob("edit/**/*.py", recursive=True) + glob.glob(
            "EditEngine/**/*.py", recursive=True
        )
        all_files.extend(code_files)

    if include_tests:
        test_files = glob.glob("edit/tests/**/*.py", recursive=True) + glob.glob(
            "tests/**/*.py", recursive=True
        )
        all_files.extend(test_files)

    return all_files


def convert_file_patterns_to_paths(
    file_patterns, include_tests=True, include_code=True
):
    """Convert file patterns to actual file paths for linting/testing.

    Args:
        file_patterns: List of file patterns (code files, test files, with/without extensions)
        include_tests: Whether to include test files in the results
        include_code: Whether to include code files in the results

    Returns:
        List of file paths that match the patterns
    """
    if not file_patterns:
        return []

    all_files = get_all_project_files(include_tests, include_code)
    return filter_files_by_patterns(
        all_files, file_patterns, include_tests, include_code
    )
