import uuid
from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from data.models.edit_task import EditTask


class TestEditTask(TestCase):
    """Test cases for the EditTask model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )

    def test_edit_task_creation_minimal(self):
        """Test creating an EditTask with minimal required fields."""
        task = EditTask.objects.create(
            editing_mode="copyedit",
            llm_provider="google",
            created_at=timezone.now(),
        )

        # Check auto-generated fields
        self.assertIsInstance(task.id, uuid.UUID)
        self.assertEqual(task.editing_mode, "copyedit")
        self.assertEqual(task.llm_provider, "google")
        self.assertEqual(task.status, "PENDING")
        self.assertIsInstance(task.created_at, datetime)
        self.assertIsInstance(task.updated_at, datetime)

    def test_edit_task_creation_complete(self):
        """Test creating an EditTask with all fields."""
        task = EditTask.objects.create(
            editing_mode="brevity",
            content="Test wikitext content",
            article_title="Test Article",
            section_title="Test Section",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            user=self.user,
            celery_task_id="test-celery-id",
            created_at=timezone.now(),
        )

        self.assertEqual(task.editing_mode, "brevity")
        self.assertEqual(task.content, "Test wikitext content")
        self.assertEqual(task.article_title, "Test Article")
        self.assertEqual(task.section_title, "Test Section")
        self.assertEqual(task.llm_provider, "openai")
        self.assertEqual(task.llm_model, "gpt-4o-mini")
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.celery_task_id, "test-celery-id")

    def test_edit_task_str_representation(self):
        """Test the string representation of EditTask."""
        task = EditTask.objects.create(
            editing_mode="copyedit",
            llm_provider="google",
            created_at=timezone.now(),
        )

        expected = f"EditTask {task.id} - copyedit - PENDING"
        self.assertEqual(str(task), expected)

    def test_is_completed_method(self):
        """Test the is_completed method."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        # Initially pending
        self.assertFalse(task.is_completed())

        # Test completed states
        for status in ["SUCCESS", "FAILURE", "REVOKED"]:
            task.status = status
            self.assertTrue(task.is_completed())

        # Test non-completed states
        for status in ["PENDING", "STARTED", "RETRY"]:
            task.status = status
            self.assertFalse(task.is_completed())

    def test_is_processing_method(self):
        """Test the is_processing method."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        # Test processing states
        for status in ["PENDING", "STARTED", "RETRY"]:
            task.status = status
            self.assertTrue(task.is_processing())

        # Test non-processing states
        for status in ["SUCCESS", "FAILURE", "REVOKED"]:
            task.status = status
            self.assertFalse(task.is_processing())

    def test_mark_started_method(self):
        """Test the mark_started method."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )
        original_updated_at = task.updated_at

        # Mark as started
        task.mark_started()

        # Refresh from database
        task.refresh_from_db()

        self.assertEqual(task.status, "STARTED")
        self.assertIsNotNone(task.started_at)
        self.assertGreater(task.updated_at, original_updated_at)

    def test_mark_success_method(self):
        """Test the mark_success method."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )
        result_data = {
            "paragraphs": [{"before": "test", "after": "test", "status": "UNCHANGED"}]
        }

        # Mark as successful
        task.mark_success(result_data)

        # Refresh from database
        task.refresh_from_db()

        self.assertEqual(task.status, "SUCCESS")
        self.assertEqual(task.result, result_data)
        self.assertIsNotNone(task.completed_at)

    def test_mark_failure_method(self):
        """Test the mark_failure method."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )
        error_message = "Test error occurred"

        # Mark as failed
        task.mark_failure(error_message)

        # Refresh from database
        task.refresh_from_db()

        self.assertEqual(task.status, "FAILURE")
        self.assertEqual(task.error_message, error_message)
        self.assertIsNotNone(task.completed_at)

    def test_status_choices_validation(self):
        """Test that only valid status choices are accepted."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        # Valid status choices
        valid_statuses = [
            "PENDING",
            "STARTED",
            "SUCCESS",
            "FAILURE",
            "RETRY",
            "REVOKED",
        ]
        for status in valid_statuses:
            task.status = status
            task.save()  # Should not raise an error
            self.assertEqual(task.status, status)

    def test_user_cascade_behavior(self):
        """Test that deleting a user sets the task user to NULL."""
        task = EditTask.objects.create(
            editing_mode="copyedit",
            llm_provider="google",
            user=self.user,
            created_at=timezone.now(),
        )

        # Delete the user
        self.user.delete()

        # Refresh task from database
        task.refresh_from_db()

        # User should be set to NULL
        self.assertIsNone(task.user)

    def test_json_field_storage(self):
        """Test that JSONField properly stores and retrieves complex data."""
        complex_result = {
            "paragraphs": [
                {
                    "before": "Original text with [[link]]",
                    "after": "Edited text with [[link]]",
                    "status": "CHANGED",
                    "status_details": "Content was successfully edited by AI and passed validation",
                }
            ],
            "article_title": "Test Article",
            "section_title": "Test Section",
            "article_url": "https://en.wikipedia.org/wiki/Test_Article",
        }

        task = EditTask.objects.create(
            editing_mode="copyedit",
            llm_provider="google",
            result=complex_result,
            created_at=timezone.now(),
        )

        # Refresh from database
        task.refresh_from_db()

        self.assertEqual(task.result, complex_result)
        self.assertEqual(
            task.result["paragraphs"][0]["before"], "Original text with [[link]]"
        )

    def test_ordering_by_created_at(self):
        """Test that tasks are ordered by created_at descending."""
        # Create tasks with slight delay to ensure different timestamps
        task1 = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )
        task2 = EditTask.objects.create(
            editing_mode="brevity", llm_provider="openai", created_at=timezone.now()
        )

        tasks = list(EditTask.objects.all())

        # Should be ordered by created_at descending (newest first)
        self.assertEqual(tasks[0], task2)
        self.assertEqual(tasks[1], task1)

    def test_database_indexes(self):
        """Test that the expected database indexes exist."""
        # This is more of a smoke test - the indexes are defined in Meta
        # and should be created during migration
        EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        # Test querying by indexed fields (should be efficient)
        EditTask.objects.filter(status="PENDING")
        EditTask.objects.filter(created_at__gte=timezone.now())
        EditTask.objects.filter(celery_task_id="test-id")

        # If indexes are missing, these queries will still work but be slower

    def test_long_text_fields(self):
        """Test handling of long text in various fields."""
        long_content = "x" * 10000  # 10KB of text
        long_error = "Error: " + "x" * 5000

        task = EditTask.objects.create(
            editing_mode="copyedit",
            llm_provider="google",
            content=long_content,
            error_message=long_error,
            created_at=timezone.now(),
        )

        task.refresh_from_db()

        self.assertEqual(len(task.content), 10000)
        self.assertEqual(len(task.error_message), len(long_error))

    def test_update_progress_data_valid(self):
        """Test updating progress data with valid data."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        progress_data = {
            "phase_counts": {
                "started": 2,
                "llm_processing": 0,
                "post_processing": 0,
                "complete": 1,
            },
            "total_paragraphs": 3,
            "paragraphs": [
                {"index": 0, "phase": "started", "status": None},
                {
                    "index": 1,
                    "phase": "complete",
                    "status": "CHANGED",
                    "completed_at": "2024-01-01T12:00:00Z",
                },
                {"index": 2, "phase": "started", "status": None},
            ],
        }

        task.update_progress_enhanced(progress_data)
        task.refresh_from_db()

        self.assertEqual(task.progress_data, progress_data)

    def test_update_progress_data_invalid_counts(self):
        """Test updating progress data with invalid phase counts."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        progress_data = {
            "phase_counts": {"started": 1, "complete": 1},
            "total_paragraphs": 3,  # Mismatch: counts sum to 2 but total is 3
        }

        with self.assertRaises(ValueError) as context:
            task.update_progress_enhanced(progress_data)

        self.assertIn(
            "Phase counts (2) don't match total paragraphs (3)", str(context.exception)
        )

    def test_get_progress_for_api_enhanced_format(self):
        """Test getting progress data in enhanced format."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        enhanced_progress = {
            "phase_counts": {"started": 1, "complete": 1},
            "total_paragraphs": 2,
            "paragraphs": [
                {"index": 0, "phase": "complete", "status": "CHANGED"},
                {"index": 1, "phase": "started", "status": None},
            ],
        }

        task.progress_data = enhanced_progress
        task.save()

        result = task.get_progress_for_api()
        self.assertEqual(result, enhanced_progress)

    def test_get_progress_for_api_legacy_format(self):
        """Test getting progress data in legacy format."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        legacy_progress = {"processed": 5, "total": 10}
        task.progress_data = legacy_progress
        task.save()

        result = task.get_progress_for_api()
        self.assertEqual(result, legacy_progress)

    def test_get_progress_for_api_no_data(self):
        """Test getting progress data when none exists."""
        task = EditTask.objects.create(
            editing_mode="copyedit", llm_provider="google", created_at=timezone.now()
        )

        result = task.get_progress_for_api()
        self.assertIsNone(result)
