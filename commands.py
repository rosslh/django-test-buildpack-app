"""Command handlers for manage.py."""

import shutil
import subprocess
import sys

from file_utils import convert_file_patterns_to_paths
from services.core.constants import DEFAULT_WORKER_CONCURRENCY
from test_coverage import run_test_coverage


def run_command(cmd):
    """Run a shell command and return its exit code."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def handle_lint():
    """Handle the lint command, with optional file arguments."""
    file_patterns = sys.argv[2:] if len(sys.argv) > 2 else []

    if file_patterns:
        # Filter files based on patterns
        target_files = convert_file_patterns_to_paths(
            file_patterns, include_tests=True, include_code=True
        )
        if not target_files:
            print(f"No files found matching patterns: {file_patterns}")
            sys.exit(1)

        files_str = " ".join(f'"{f}"' for f in target_files)
        print(f"Linting {len(target_files)} file(s) matching patterns: {file_patterns}")

        exit_code = run_command(f"ruff check {files_str}")
        if exit_code == 0:
            exit_code = run_command(f"mypy {files_str}")
    else:
        # Lint everything
        exit_code = run_command("ruff check .")
        if exit_code == 0:
            exit_code = run_command("mypy .")

    sys.exit(exit_code)


def handle_lint_fix():
    """Handle the lint:fix command."""
    exit_code = 0
    exit_code |= run_command("ruff check --fix .")
    exit_code |= run_command("ruff format .")
    print(
        "All auto-fixes applied. Run 'python manage.py lint' to check remaining issues."
    )
    sys.exit(exit_code)


def handle_format():
    """Handle the format command."""
    exit_code = run_command("ruff format .")
    sys.exit(exit_code)


def handle_format_check():
    """Handle the format:check command."""
    exit_code = run_command("ruff format --check .")
    sys.exit(exit_code)


def handle_test():
    """Handle the test command, with optional file arguments."""
    raw_args = sys.argv[2:]

    # Separate file patterns from pytest arguments
    file_patterns = []
    pytest_args = []

    for arg in raw_args:
        if arg in ("--update", "-u"):
            pytest_args.append("--snapshot-update")
        elif arg.startswith("-"):
            # This is a pytest argument
            pytest_args.append(arg)
        else:
            # This might be a file pattern
            file_patterns.append(arg)

    if file_patterns:
        # Filter test files based on patterns
        target_files = convert_file_patterns_to_paths(
            file_patterns, include_tests=True, include_code=False
        )
        if not target_files:
            print(f"No test files found matching patterns: {file_patterns}")
            sys.exit(1)

        files_str = " ".join(f'"{f}"' for f in target_files)
        print(
            f"Running tests for {len(target_files)} file(s) matching patterns: {file_patterns}"
        )

        # Combine filtered files with pytest arguments
        all_args = [files_str] + pytest_args
        exit_code = run_command(f"python -m pytest {' '.join(all_args)}")
    else:
        # Run all tests with any provided pytest arguments
        exit_code = run_command(f"python -m pytest {' '.join(pytest_args)}")

    sys.exit(exit_code)


def handle_test_coverage():
    """Handle the test:coverage command."""
    # Get any file arguments passed after the command
    test_args = sys.argv[2:] if len(sys.argv) > 2 else []
    run_test_coverage(test_args)


def handle_celery():
    """Handle the celery command, passing through all arguments to celery CLI."""
    celery_exe = shutil.which("celery")
    if not celery_exe:
        print("Celery is not installed or not found in PATH.")
        sys.exit(1)
    # Pass all arguments after 'celery' to the celery CLI
    celery_args = sys.argv[2:]
    # Default to using the EditEngine app if not specified
    if not any(arg.startswith("-A") or arg == "-A" for arg in celery_args):
        celery_args = ["-A", "EditEngine"] + celery_args

    # Add default concurrency for worker commands if not already specified
    # This sets the Celery worker task concurrency to match the LLM API semaphore limit
    # for optimal throughput and consistent rate limiting behavior
    if (len(celery_args) >= 2 and celery_args[-2:] == ["EditEngine", "worker"]) or (
        "worker" in celery_args
        and not any(arg.startswith("--concurrency") for arg in celery_args)
    ):
        if "worker" in celery_args:
            celery_args.append(f"--concurrency={DEFAULT_WORKER_CONCURRENCY}")

    cmd = f'"{celery_exe}" {" ".join(celery_args)}'
    sys.exit(run_command(cmd))
