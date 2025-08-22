import os
from unittest.mock import MagicMock, patch

# Configure Django settings before importing Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")

import django
from django.conf import settings
from django.test import TestCase

from api.exceptions.user_facing_exceptions import APIKeyError

if not settings.configured:
    django.setup()

from data.models.edit_task import EditTask
from services.tasks.edit_task_service import EditTaskService


class TestEditTaskService(TestCase):
    """Test EditTaskService class."""

    def test_create_llm_config_google(self):
        """Test creating LLM config with Google API key."""
        config = EditTaskService.create_llm_config("google_key", None, None, None, None)
        self.assertEqual(config["provider"], "google")
        self.assertEqual(config["api_key"], "google_key")

    def test_create_llm_config_openai(self):
        """Test creating LLM config with OpenAI API key."""
        config = EditTaskService.create_llm_config(None, "openai_key", None, None, None)
        self.assertEqual(config["provider"], "openai")
        self.assertEqual(config["api_key"], "openai_key")

    def test_create_llm_config_anthropic(self):
        """Test creating LLM config with Anthropic API key."""
        config = EditTaskService.create_llm_config(
            None, None, "anthropic_key", None, None
        )
        self.assertEqual(config["provider"], "anthropic")
        self.assertEqual(config["api_key"], "anthropic_key")

    def test_create_llm_config_mistral(self):
        """Test creating LLM config with Mistral API key."""
        config = EditTaskService.create_llm_config(
            None, None, None, "mistral_key", None
        )
        self.assertEqual(config["provider"], "mistral")
        self.assertEqual(config["api_key"], "mistral_key")

    def test_create_llm_config_perplexity(self):
        """Test creating LLM config with Perplexity API key."""
        config = EditTaskService.create_llm_config(
            None, None, None, None, "perplexity_key"
        )
        self.assertEqual(config["provider"], "perplexity")
        self.assertEqual(config["api_key"], "perplexity_key")

    def test_create_llm_config_no_keys(self):
        """Test creating LLM config with no API keys."""
        with self.assertRaises(APIKeyError) as cm:
            EditTaskService.create_llm_config(None, None, None, None, None)
        self.assertIn("API key required", str(cm.exception))

    def test_validate_api_keys_google(self):
        """Test validating API keys with Google key."""
        result = EditTaskService.validate_api_keys("google_key", None, None, None, None)
        self.assertTrue(result)

    def test_validate_api_keys_openai(self):
        """Test validating API keys with OpenAI key."""
        result = EditTaskService.validate_api_keys(None, "openai_key", None, None, None)
        self.assertTrue(result)

    def test_validate_api_keys_anthropic(self):
        """Test validating API keys with Anthropic key."""
        result = EditTaskService.validate_api_keys(
            None, None, "anthropic_key", None, None
        )
        self.assertTrue(result)

    def test_validate_api_keys_mistral(self):
        """Test validating API keys with Mistral key."""
        result = EditTaskService.validate_api_keys(
            None, None, None, "mistral_key", None
        )
        self.assertTrue(result)

    def test_validate_api_keys_perplexity(self):
        """Test validating API keys with Perplexity key."""
        result = EditTaskService.validate_api_keys(
            None, None, None, None, "perplexity_key"
        )
        self.assertTrue(result)

    def test_validate_api_keys_both(self):
        """Test validating API keys with both keys."""
        result = EditTaskService.validate_api_keys(
            "google_key", "openai_key", None, None, None
        )
        self.assertTrue(result)

    def test_validate_api_keys_none(self):
        """Test validating API keys with no keys."""
        result = EditTaskService.validate_api_keys(None, None, None, None, None)
        self.assertFalse(result)

    def test_create_edit_task_with_article_title(self):
        """Test creating edit task with article title."""
        llm_config = {"provider": "openai", "model": "gpt-4"}
        task = EditTaskService.create_edit_task(
            editing_mode="brevity",
            article_title="Test Article",
            section_title="Test Section",
            llm_config=llm_config,
        )

        self.assertEqual(task.editing_mode, "brevity")
        self.assertEqual(task.article_title, "Test Article")
        self.assertEqual(task.section_title, "Test Section")
        self.assertEqual(task.llm_provider, "openai")
        self.assertEqual(task.llm_model, "gpt-4")

    def test_build_task_kwargs_with_article_title(self):
        """Test building task kwargs with article title."""
        kwargs = EditTaskService.build_task_kwargs(
            edit_task_id="test-id",
            article_title="Test Article",
            section_title="Test Section",
        )

        self.assertEqual(kwargs["edit_task_id"], "test-id")
        self.assertEqual(kwargs["article_title"], "Test Article")
        self.assertEqual(kwargs["section_title"], "Test Section")
        self.assertNotIn("content", kwargs)

    @patch("services.tasks.edit_task_service.EncryptionService")
    @patch("services.tasks.edit_task_service.process_edit_task_batched")
    def test_start_processing_task(self, mock_process_task, mock_encryption_service):
        """Test starting processing task."""
        mock_celery_task = MagicMock()
        mock_celery_task.id = "celery-task-id"
        mock_process_task.delay.return_value = mock_celery_task

        # Mock encryption service
        mock_encryption = MagicMock()
        mock_encryption.encrypt_dict.return_value = "encrypted_config"
        mock_encryption_service.return_value = mock_encryption

        llm_config = {"provider": "google", "api_key": "test_key"}
        task_kwargs = {"edit_task_id": "test-id", "content": "test content"}

        result = EditTaskService.start_processing_task(
            editing_mode="copyedit", llm_config=llm_config, task_kwargs=task_kwargs
        )

        self.assertEqual(result, "celery-task-id")
        mock_encryption.encrypt_dict.assert_called_once_with(llm_config)
        mock_process_task.delay.assert_called_once_with(
            editing_mode="copyedit",
            encrypted_llm_config="encrypted_config",
            edit_task_id="test-id",
            content="test content",
        )

    def test_update_task_with_celery_id(self):
        """Test updating task with Celery ID."""
        task = EditTask.objects.create(
            editing_mode="copyedit",
            content="Test content",
            llm_provider="google",
            status="PENDING",
        )

        EditTaskService.update_task_with_celery_id(task, "celery-task-id")

        # Refresh from database
        task.refresh_from_db()
        self.assertEqual(task.celery_task_id, "celery-task-id")

    @patch("services.tasks.edit_task_service.process_edit_task_batched")
    def test_create_and_start_edit_task_success(self, mock_process_task):
        """Test complete workflow for creating and starting edit task."""
        mock_celery_task = MagicMock()
        mock_celery_task.id = "celery-task-id"
        mock_process_task.delay.return_value = mock_celery_task

        result = EditTaskService.create_and_start_edit_task(
            editing_mode="copyedit",
            article_title="Test Article",
            section_title="Test Section",
            google_api_key="google_key",
            openai_api_key=None,
            anthropic_api_key=None,
            mistral_api_key=None,
            perplexity_api_key=None,
        )

        self.assertIn("task_id", result)
        self.assertIn("status_url", result)
        self.assertTrue(result["status_url"].endswith(result["task_id"]))

        # Verify task was created
        task = EditTask.objects.get(id=result["task_id"])
        self.assertEqual(task.editing_mode, "copyedit")
        self.assertEqual(task.llm_provider, "google")
        self.assertEqual(task.celery_task_id, "celery-task-id")

    @patch("services.tasks.edit_task_service.process_edit_task_batched")
    def test_create_and_start_edit_task_with_article_title(self, mock_process_task):
        """Test creating and starting edit task with article title."""
        mock_celery_task = MagicMock()
        mock_celery_task.id = "celery-task-id"
        mock_process_task.delay.return_value = mock_celery_task

        result = EditTaskService.create_and_start_edit_task(
            editing_mode="brevity",
            article_title="Test Article",
            section_title="Test Section",
            google_api_key=None,
            openai_api_key="openai_key",
            anthropic_api_key=None,
            mistral_api_key=None,
            perplexity_api_key=None,
        )

        self.assertIn("task_id", result)
        self.assertIn("status_url", result)

        # Verify task was created
        task = EditTask.objects.get(id=result["task_id"])
        self.assertEqual(task.editing_mode, "brevity")
        self.assertIsNone(task.content)
        self.assertEqual(task.article_title, "Test Article")
        self.assertEqual(task.section_title, "Test Section")
        self.assertEqual(task.llm_provider, "openai")

    def test_create_and_start_edit_task_no_api_key(self):
        """Test creating and starting edit task with no API key."""
        with self.assertRaises(APIKeyError) as cm:
            EditTaskService.create_and_start_edit_task(
                editing_mode="copyedit",
                article_title="Test Article",
                section_title="Test Section",
                google_api_key=None,
                openai_api_key=None,
                anthropic_api_key=None,
                mistral_api_key=None,
                perplexity_api_key=None,
            )
        self.assertIn("API key required", str(cm.exception))

    @patch("services.tasks.edit_task_service.process_edit_task_batched")
    def test_create_and_start_edit_task_celery_failure(self, mock_process_task):
        """Test handling Celery task failure."""
        mock_process_task.delay.side_effect = Exception("Celery error")

        with self.assertRaises(Exception) as cm:
            EditTaskService.create_and_start_edit_task(
                editing_mode="copyedit",
                article_title="Test Article",
                section_title="Test Section",
                google_api_key="google_key",
                openai_api_key=None,
                anthropic_api_key=None,
                mistral_api_key=None,
                perplexity_api_key=None,
            )
        self.assertIn("Celery error", str(cm.exception))

        # Verify task was still created even if Celery failed
        tasks = EditTask.objects.filter(editing_mode="copyedit")
        self.assertEqual(tasks.count(), 1)
