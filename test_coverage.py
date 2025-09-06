#!/usr/bin/env python
"""Test coverage utilities for individual file coverage checks."""

import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from file_utils import filter_files_by_patterns

# Load test environment variables
load_dotenv(".env.test")

# Multiple code roots for the new three-tier architecture
CODE_ROOTS = [Path("api"), Path("services"), Path("data")]
TEST_ROOT = Path("tests")
EXCLUDE_DIRS = {"__pycache__", "migrations"}
EXCLUDE_FILES = {"__init__.py", "run_tests.py", "wiki_link_validator.py"}


def get_code_files():
    """Get all code files in the api, services, and data directories."""
    code_files = []
    for code_root in CODE_ROOTS:
        if not code_root.exists():
            continue
        for root, dirs, files in os.walk(code_root):
            # Exclude certain directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if (
                    file.endswith(".py")
                    and file not in EXCLUDE_FILES
                    and not file.startswith("test_")
                ):
                    # Get the path relative to project root, including the tier directory
                    rel_path = Path(root)
                    code_files.append((rel_path, file))
    return code_files


def code_to_test_path(rel_path, code_file):
    """Map code file to test file path, mirroring the directory structure."""
    # e.g. services/foo/bar.py -> tests/services/foo/test_bar.py
    # e.g. api/views/edit_views.py -> tests/api/views/test_edit_views.py
    test_dir = TEST_ROOT / rel_path

    # Special case: constants.py in services/core directory maps to test_constants.py
    if str(rel_path) == "services/core" and code_file == "constants.py":
        test_file = "test_constants.py"
    else:
        test_file = f"test_{code_file}"
    return test_dir / test_file


def get_test_files():
    """Return a list of all test files (relative to TEST_ROOT)."""
    test_files: List[Tuple[Path, str]] = []
    if not TEST_ROOT.exists():
        return test_files
    for root, dirs, files in os.walk(TEST_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                # Get the path relative to TEST_ROOT, including all subdirectories
                rel_path = Path(root).relative_to(TEST_ROOT)
                test_files.append((rel_path, file))
    return test_files


def _check_missing_test_files():
    """Check for missing test files and return list of missing ones."""
    missing = []
    for rel_path, code_file in get_code_files():
        test_path = code_to_test_path(rel_path, code_file)
        if not test_path.exists():
            missing.append(str(test_path))
    return missing


def _check_extra_test_files():
    """Check for extra test files and return list of extra ones."""
    extra = []
    for rel_path, test_file in get_test_files():
        # Special case: test_constants.py maps to constants.py in services/core
        if test_file == "test_constants.py" and str(rel_path) == "services/core":
            code_file = "constants.py"
        else:
            # Remove 'test_' prefix to get the code file name
            code_file = test_file[len("test_") :]

        # Reconstruct the code path based on the test path
        code_path = rel_path / code_file
        # Check if this code file exists in any of our code roots
        exists = False
        for code_root in CODE_ROOTS:
            if (code_root / code_path.relative_to(code_path.parts[0])).exists():
                exists = True
                break

        if not exists:
            extra.append(str(TEST_ROOT / rel_path / test_file))
    return extra


def validate_test_file_mapping():
    """Validate that every code file has a test and no extra tests exist."""
    print("Validating test file mapping...")

    # Check for missing test files
    missing = _check_missing_test_files()

    # Check for extra test files
    extra = _check_extra_test_files()

    # Report errors and exit if any found
    errors = []
    if missing:
        errors.append(f"Missing test files for: {missing}")
    if extra:
        errors.append(f"Extra test files without code: {extra}")

    if errors:
        print("❌ Test file mapping validation failed:")
        for error in errors:
            print(f"   {error}")
        sys.exit(1)

    print("✅ Test file mapping validation passed.")


def get_source_file_for_test(test_file):
    """Find the source file corresponding to a test file."""
    p = Path(test_file)
    if p.parts[0] != "tests":
        return None

    # Special case: test_constants.py in services/core maps to constants.py
    if (
        p.name == "test_constants.py"
        and len(p.parts) > 2
        and p.parts[1] == "services"
        and p.parts[2] == "core"
    ):
        source_filename = "constants.py"
    else:
        source_filename = p.stem.replace("test_", "") + ".py"

    # E.g., tests/services/core/test_foo.py -> services/core/foo.py
    # E.g., tests/api/views/test_edit_views.py -> api/views/edit_views.py
    source_rel_path = Path(*p.parts[1:]).with_name(source_filename)

    # Check for the source file - it should be in the same relative path structure
    potential_path = source_rel_path
    if potential_path.exists():
        return str(potential_path)

    return None


def run_individual_coverage_test(test_file, source_file):
    """Run coverage test for a specific test file against its source file."""
    with tempfile.NamedTemporaryFile(suffix=".coverage") as cov_file:
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "EditEngine.settings"
        env["DJANGO_CONFIGURATION"] = "Development"  # Ensure Django configuration is set
        env["COVERAGE_FILE"] = cov_file.name

        cov_run_cmd = (
            f"DJANGO_CONFIGURATION=Development DJANGO_SETTINGS_MODULE=EditEngine.settings "
            f"python3 -m coverage run --data-file='{cov_file.name}' "
            f"--source='.' --omit='*/migrations/*,*/tests/*' "
            f"-m pytest -c pytest.coverage.ini --cov-context=test {test_file}"
        )
        run_result = subprocess.run(
            cov_run_cmd, shell=True, capture_output=True, text=True, env=env
        )

        if run_result.returncode != 0 and run_result.returncode != 5:
            print(f"\n{'=' * 60}")
            print(f"Testing coverage: {test_file} -> {source_file}")
            print(f"{'=' * 60}")
            print(f"❌ Pytest failed for {test_file}")
            print(run_result.stdout)
            print(run_result.stderr)
            return False

        cov_report_cmd = (
            f"python3 -m coverage report --data-file='{cov_file.name}' "
            f"--fail-under=99 --show-missing {source_file}"
        )
        report_result = subprocess.run(
            cov_report_cmd, shell=True, capture_output=True, text=True, env=env
        )

        if report_result.returncode != 0:
            print(f"\n{'=' * 60}")
            print(f"Testing coverage: {test_file} -> {source_file}")
            print(f"{'=' * 60}")
            print(report_result.stdout)
            # Print uncovered line numbers if present in the report
            for line in report_result.stdout.splitlines():
                if source_file in line and "missing" in line:
                    # The last column should be the missing lines
                    parts = line.split()
                    if len(parts) >= 6:
                        missing = parts[-1]
                        print(f"Uncovered lines in {source_file}: {missing}")
            print(f"❌ Coverage failed for {source_file} (from {test_file})")
            print(report_result.stderr)
            return False

    return True


def filter_test_files(test_files, file_patterns):
    """Filter test files based on provided patterns.

    Accepts both test file names and code file names, with or without extensions.
    Code file names are converted to their corresponding test file names.
    """
    return filter_files_by_patterns(
        test_files,
        file_patterns,
        include_tests=True,
        include_code=False,
        error_message_prefix="test files",
    )


def run_test_coverage(file_patterns=None):
    """Run coverage tests for each file individually.

    Args:
        file_patterns: Optional list of file patterns to filter test files.
                      If provided, only test files matching these patterns will be run.
    """
    # First, validate that all code files have tests and no extra tests exist
    validate_test_file_mapping()

    fail_fast = False
    print("Running per-file coverage checks...")
    test_files = glob.glob("tests/**/test_*.py", recursive=True)

    if not test_files:
        print("No test files found.")
        sys.exit(1)

    # Filter test files if patterns are provided
    if file_patterns:
        test_files = filter_test_files(test_files, file_patterns)
        print(f"Running coverage for {len(test_files)} filtered test file(s)")

    all_passed = True
    for test_file in sorted(test_files):
        source_file = get_source_file_for_test(test_file)
        if source_file:
            if not run_individual_coverage_test(test_file, source_file):
                all_passed = False
                if fail_fast:
                    sys.exit(1)

    if all_passed:
        print("\n✅ All files passed coverage checks.")
        sys.exit(0)
    else:
        print("\n❌ Some files failed coverage checks.")
        sys.exit(1)


if __name__ == "__main__":
    # Get command-line arguments excluding the script name
    file_patterns = sys.argv[1:] if len(sys.argv) > 1 else None
    run_test_coverage(file_patterns)
