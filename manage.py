#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from commands import (
    handle_celery,
    handle_format,
    handle_format_check,
    handle_lint,
    handle_lint_fix,
    handle_test,
    handle_test_coverage,
)


def handle_custom_commands():
    """Handle custom lint/format/test commands."""
    if len(sys.argv) < 2:
        return False
    command = sys.argv[1]
    if command == "lint":
        handle_lint()
        return True
    elif command == "lint:fix":
        handle_lint_fix()
        return True
    elif command == "format":
        handle_format()
        return True
    elif command == "format:check":
        handle_format_check()
        return True
    elif command == "test":
        handle_test()
        return True
    elif command == "test:coverage":
        handle_test_coverage()
        return True
    elif command == "celery":
        handle_celery()
        return True
    return False


def main():
    """Run administrative tasks."""
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Handle custom commands first
    if handle_custom_commands():
        return

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")
    os.environ.setdefault("DJANGO_CONFIGURATION", "Production")
    try:
        from configurations.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
