"""Django management command for Celery worker with environment variable support."""

import os
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run Celery worker with configurable settings from environment variables"

    def add_arguments(self, parser):
        parser.add_argument(
            "command", nargs="?", default="worker", help="Celery command (default: worker)"
        )
        parser.add_argument(
            "--concurrency",
            "-c",
            type=int,
            help="Number of concurrent worker processes/threads/green threads",
        )
        parser.add_argument(
            "--loglevel", "-l", default="info", help="Logging level (default: info)"
        )
        parser.add_argument(
            "--max-tasks-per-child",
            type=int,
            help="Maximum number of tasks per child process before recycling",
        )
        parser.add_argument(
            "--purge", action="store_true", help="Purge all waiting tasks before start"
        )
        parser.add_argument(
            "--pool",
            "-P",
            choices=["prefork", "eventlet", "gevent", "solo"],
            help="Worker pool implementation (prefork|eventlet|gevent|solo)",
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        # Build the celery command
        celery_cmd = self._build_celery_command(options)

        # Display the command being executed
        self.stdout.write(
            self.style.SUCCESS(f"Executing: {' '.join(celery_cmd)}")
        )

        # Execute the celery command
        os.execvp(celery_cmd[0], celery_cmd)

    def _build_celery_command(self, options) -> List[str]:
        """Build the celery command with all arguments."""
        cmd = ["celery", "-A", "EditEngine"]

        # Add the celery command (worker, beat, etc.)
        cmd.append(options["command"])

        if options["command"] == "worker":
            # Add concurrency setting
            concurrency = options.get("concurrency")
            if concurrency is None:
                # Get from settings, which will raise ImproperlyConfigured if not set
                concurrency = settings.CELERY_WORKER_CONCURRENCY
            cmd.extend(["--concurrency", str(concurrency)])

            # Add pool implementation
            pool = options.get("pool")
            if pool is None:
                # Get from environment variable, default to prefork (eventlet has Python 3.13 compatibility issues)
                pool = os.environ.get("CELERY_WORKER_POOL", "prefork")
            cmd.extend(["--pool", pool])

            # Add log level
            cmd.extend(["--loglevel", options["loglevel"]])

            # Add max tasks per child if specified
            max_tasks = options.get("max_tasks_per_child")
            if max_tasks is None:
                # Get from settings, which will raise ImproperlyConfigured if not set
                max_tasks = settings.CELERY_MAX_TASKS_PER_CHILD
            if max_tasks > 0:
                cmd.extend(["--max-tasks-per-child", str(max_tasks)])

            # Add purge option
            if options["purge"]:
                cmd.append("--purge")

        return cmd
