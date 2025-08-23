"""Tests for the Celery management command."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from services.management.commands.celery import Command


class TestCeleryCommand(TestCase):
    """Test the Celery management command."""

    def setUp(self):
        """Set up test fixtures."""
        self.command = Command()

    @override_settings(CELERY_WORKER_CONCURRENCY=4, CELERY_MAX_TASKS_PER_CHILD=200)
    @patch("os.execvp")
    def test_default_worker_command(self, mock_execvp):
        """Test default worker command execution."""
        options = {
            "command": "worker",
            "concurrency": None,
            "loglevel": "info",
            "max_tasks_per_child": None,
            "purge": False,
            "pool": None,
        }
        self.command.handle(**options)

        expected_cmd = [
            "celery",
            "-A",
            "EditEngine",
            "worker",
            "--concurrency",
            "4",
            "--pool",
            "prefork",
            "--loglevel",
            "info",
            "--max-tasks-per-child",
            "200",
        ]
        mock_execvp.assert_called_once_with("celery", expected_cmd)

    @override_settings(CELERY_WORKER_CONCURRENCY=2, CELERY_MAX_TASKS_PER_CHILD=0)
    @patch("os.execvp")
    def test_worker_with_zero_max_tasks(self, mock_execvp):
        """Test worker command with zero max tasks (disabled)."""
        options = {
            "command": "worker",
            "concurrency": None,
            "loglevel": "info",
            "max_tasks_per_child": None,
            "purge": False,
            "pool": None,
        }
        self.command.handle(**options)

        expected_cmd = [
            "celery",
            "-A",
            "EditEngine",
            "worker",
            "--concurrency",
            "2",
            "--pool",
            "prefork",
            "--loglevel",
            "info",
        ]
        mock_execvp.assert_called_once_with("celery", expected_cmd)

    @override_settings(CELERY_WORKER_CONCURRENCY=8, CELERY_MAX_TASKS_PER_CHILD=150)
    @patch("os.execvp")
    def test_worker_with_custom_options(self, mock_execvp):
        """Test worker command with custom options."""
        options = {
            "command": "worker",
            "concurrency": 6,
            "loglevel": "debug",
            "max_tasks_per_child": 100,
            "purge": True,
            "pool": None,
        }
        self.command.handle(**options)

        expected_cmd = [
            "celery",
            "-A",
            "EditEngine",
            "worker",
            "--concurrency",
            "6",
            "--pool",
            "prefork",
            "--loglevel",
            "debug",
            "--max-tasks-per-child",
            "100",
            "--purge",
        ]
        mock_execvp.assert_called_once_with("celery", expected_cmd)

    @patch("os.execvp")
    def test_non_worker_command(self, mock_execvp):
        """Test non-worker celery command."""
        options = {"command": "beat", "loglevel": "info"}
        self.command.handle(**options)

        expected_cmd = ["celery", "-A", "EditEngine", "beat"]
        mock_execvp.assert_called_once_with("celery", expected_cmd)

    def test_build_celery_command_worker(self):
        """Test building worker command."""
        options = {
            "command": "worker",
            "concurrency": 4,
            "loglevel": "info",
            "max_tasks_per_child": 200,
            "purge": False,
            "pool": None,
        }

        with override_settings(
            CELERY_WORKER_CONCURRENCY=2, CELERY_MAX_TASKS_PER_CHILD=100
        ):
            cmd = self.command._build_celery_command(options)

            expected = [
                "celery",
                "-A",
                "EditEngine",
                "worker",
                "--concurrency",
                "4",
                "--pool",
                "prefork",
                "--loglevel",
                "info",
                "--max-tasks-per-child",
                "200",
            ]
            self.assertEqual(cmd, expected)

    def test_build_celery_command_beat(self):
        """Test building beat command."""
        options = {"command": "beat", "loglevel": "info"}
        cmd = self.command._build_celery_command(options)

        expected = ["celery", "-A", "EditEngine", "beat"]
        self.assertEqual(cmd, expected)

    @override_settings(CELERY_WORKER_CONCURRENCY=4, CELERY_MAX_TASKS_PER_CHILD=200)
    def test_build_celery_command_uses_settings_defaults(self):
        """Test that command uses settings when options not provided."""
        options = {
            "command": "worker",
            "concurrency": None,
            "loglevel": "info",
            "max_tasks_per_child": None,
            "purge": False,
            "pool": None,
        }

        cmd = self.command._build_celery_command(options)

        expected = [
            "celery",
            "-A",
            "EditEngine",
            "worker",
            "--concurrency",
            "4",
            "--pool",
            "prefork",
            "--loglevel",
            "info",
            "--max-tasks-per-child",
            "200",
        ]
        self.assertEqual(cmd, expected)

    def test_add_arguments(self):
        """Test that all expected arguments are added to the parser."""
        from argparse import ArgumentParser

        parser = ArgumentParser()

        self.command.add_arguments(parser)

        # Check that all expected arguments were added
        actions = {action.dest: action for action in parser._actions}

        # Check positional argument
        self.assertIn("command", actions)
        self.assertEqual(actions["command"].nargs, "?")
        self.assertEqual(actions["command"].default, "worker")

        # Check optional arguments
        self.assertIn("concurrency", actions)
        self.assertEqual(actions["concurrency"].type, int)

        self.assertIn("loglevel", actions)
        self.assertEqual(actions["loglevel"].default, "info")

        self.assertIn("max_tasks_per_child", actions)
        self.assertEqual(actions["max_tasks_per_child"].type, int)

        self.assertIn("pool", actions)
        self.assertEqual(
            actions["pool"].choices, ["prefork", "eventlet", "gevent", "solo"]
        )

        self.assertIn("purge", actions)
        self.assertEqual(actions["purge"].__class__.__name__, "_StoreTrueAction")
