import os
import uuid
from datetime import datetime, timezone

# Configure Django settings before importing Django or DRF modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()

from typing import Any, Dict
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from data.models.edit_task import EditTask

# Import is used implicitly by Django URL routing


class MockAsyncResult:
    def __init__(self, id, result=None):
        self.id = id
        self.result = result


class TestEditViewDRF(TestCase):
    """Test EditView class using DRF testing patterns."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.patcher = patch("services.tasks.edit_tasks.process_edit_task.delay")
        cls.mock_delay = cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.mock_delay.reset_mock()
        self.client.raise_request_exception = False
        # Always return a mock AsyncResult for .delay
        mock_result = MagicMock()
        mock_result.id = "mock-task-id"
        mock_result.result = None
        self.mock_delay.return_value = mock_result

    def test_api_keys_now_header_based(self):
        """Test that API keys are now header-based, not environment variables."""
        # API keys should no longer be in settings
        self.assertFalse(hasattr(settings, "GOOGLE_API_KEY"))
        self.assertFalse(hasattr(settings, "OPENAI_API_KEY"))

    def test_post_valid_brevity_mode_article_title_google(self):
        self.mock_delay.return_value = MockAsyncResult("mock-celery-task-id")
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)
        # Verify the task_id is a valid UUID (EditTask ID, not Celery task ID)
        uuid.UUID(response.data["task_id"])

    def test_post_valid_brevity_mode_article_title_openai(self):
        self.mock_delay.return_value = MockAsyncResult("mock-celery-task-id-2")
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_OPENAI_API_KEY="test_openai_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)
        # Verify the task_id is a valid UUID (EditTask ID, not Celery task ID)
        uuid.UUID(response.data["task_id"])

    def test_post_valid_copyedit_mode_article_title(self):
        self.mock_delay.return_value = MockAsyncResult("mock-celery-task-id-4")
        request_data = {
            "article_title": "Python (programming language)",
            "section_title": "History",
        }
        response = self.client.post(
            "/api/edit/copyedit",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)
        # Verify the task_id is a valid UUID (EditTask ID, not Celery task ID)
        uuid.UUID(response.data["task_id"])

    def test_post_invalid_editing_mode(self):
        """Test POST request with invalid editing mode."""
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/invalid_mode", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "Invalid editing mode 'invalid_mode'. Must be 'brevity' or 'copyedit'.",
        )

    def test_post_no_input_provided(self):
        """Test POST request with no input provided."""
        request_data: Dict[str, Any] = {}
        response = self.client.post(
            "/api/edit/brevity", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_post_empty_article_title(self):
        """Test POST request with empty article_title."""
        request_data = {"article_title": "", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_post_missing_api_key(self):
        """Test POST request when no API key headers are provided."""
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["error"],
            "API key required. Provide one of: X-Google-API-Key, X-OpenAI-API-Key, X-Anthropic-API-Key, X-Mistral-API-Key, or X-Perplexity-API-Key header",
        )

    def test_post_editor_exception_article_title(self):
        # Simulate task always accepted; error is handled via results endpoint, not here
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)

    def test_post_wikipedia_article_not_found(self):
        request_data = {
            "article_title": "NonExistentArticle",
            "section_title": "History",
        }
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)

    def test_post_wikipedia_api_error(self):
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)

    def test_post_llm_init_error(self):
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)

    def test_post_wiki_editor_init_error(self):
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)

    def test_post_section_not_found_error(self):
        request_data = {
            "article_title": "Apollo",
            "section_title": "NonExistentSection",
        }
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)

        # Verify the task_id is a valid UUID (EditTask ID, not Celery task ID)
        uuid.UUID(response.data["task_id"])

    def test_post_empty_paragraph_results_filtered_article_title(self):
        self.mock_delay.return_value = MockAsyncResult("mock-celery-task-id")
        request_data = {"article_title": "Apollo", "section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity",
            data=request_data,
            format="json",
            HTTP_X_GOOGLE_API_KEY="test_google_key",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("status_url", response.data)
        # Verify the task_id is a valid UUID (EditTask ID, not Celery task ID)
        uuid.UUID(response.data["task_id"])

    def test_post_only_article_title(self):
        """Test POST request with only article_title provided (should require section_title)."""
        request_data = {"article_title": "Apollo"}
        response = self.client.post(
            "/api/edit/brevity", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_post_only_section_title(self):
        """Test POST request with only section_title provided (should require article_title)."""
        request_data = {"section_title": "History"}
        response = self.client.post(
            "/api/edit/brevity", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)


class TestSectionHeadingsViewDRF(TestCase):
    """Test SectionHeadingsView class using DRF testing patterns."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()

    @patch("api.views.edit_views.SectionHeadingsService")
    def test_post_valid_article_title(self, mock_service_class):
        """Test POST request with valid article title."""
        # Mock SectionHeadingsService
        mock_service_instance = MagicMock()
        mock_service_instance.get_section_headings.return_value = {
            "headings": [
                {"text": "Overview", "level": 2},
                {"text": "History", "level": 2},
            ],
            "article_title": "Apollo",
            "article_url": "https://en.wikipedia.org/wiki/Apollo",
        }
        mock_service_class.return_value = mock_service_instance

        # Create request data
        request_data = {"article_title": "Apollo"}

        response = self.client.post(
            "/api/section-headings", data=request_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("headings", response.data)
        self.assertEqual(len(response.data["headings"]), 2)
        self.assertEqual(response.data["headings"][0]["text"], "Overview")
        self.assertEqual(response.data["headings"][0]["level"], 2)
        self.assertEqual(response.data["headings"][1]["text"], "History")
        self.assertEqual(response.data["headings"][1]["level"], 2)
        self.assertEqual(response.data["article_title"], "Apollo")
        self.assertEqual(
            response.data["article_url"], "https://en.wikipedia.org/wiki/Apollo"
        )

    def test_post_invalid_serializer_missing_article_title(self):
        """Test POST request with missing article_title."""
        request_data: Dict[str, Any] = {}
        response = self.client.post(
            "/api/section-headings", data=request_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_post_invalid_article_title_response(self):
        """Test POST request with None article_title (edge case)."""
        # This tests the _invalid_article_title_response method by using the client

        # Mock the serializer to be valid but return None for article_title
        with patch(
            "api.views.edit_views.SectionHeadingsRequestSerializer"
        ) as mock_serializer_class:
            mock_serializer = MagicMock()
            mock_serializer.is_valid.return_value = True
            mock_serializer.validated_data = {"article_title": None}
            mock_serializer_class.return_value = mock_serializer

            response = self.client.post(
                "/api/section-headings", {"article_title": None}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["error"], "Article title must be provided")

    @patch("api.views.edit_views.SectionHeadingsService")
    def test_post_wikipedia_api_error_not_found(self, mock_service_class):
        """Test POST request when Wikipedia API raises error with 'not found'."""
        from services.utils.wikipedia_api import WikipediaAPIError

        # Mock SectionHeadingsService to raise error
        mock_service_instance = MagicMock()
        mock_service_instance.get_section_headings.side_effect = WikipediaAPIError(
            "Article not found: NonExistentArticle"
        )
        mock_service_class.return_value = mock_service_instance

        # Create request data
        request_data = {"article_title": "NonExistentArticle"}

        response = self.client.post(
            "/api/section-headings", data=request_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["error"],
            "The requested article or section could not be found. Please check the article title and section title.",
        )

    @patch("api.views.edit_views.SectionHeadingsService")
    def test_post_wikipedia_api_error_general(self, mock_service_class):
        """Test POST request when Wikipedia API raises general error."""
        from services.utils.wikipedia_api import WikipediaAPIError

        # Mock SectionHeadingsService to raise error
        mock_service_instance = MagicMock()
        mock_service_instance.get_section_headings.side_effect = WikipediaAPIError(
            "API rate limit exceeded"
        )
        mock_service_class.return_value = mock_service_instance

        # Create request data
        request_data = {"article_title": "Apollo"}

        response = self.client.post(
            "/api/section-headings", data=request_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            response.data["error"],
            "Request rate limit exceeded. Please wait before trying again.",
        )

    @patch("api.views.edit_views.SectionHeadingsService")
    def test_post_unexpected_error(self, mock_service_class):
        """Test POST request when unexpected error occurs."""
        # Mock SectionHeadingsService to raise unexpected error
        mock_service_instance = MagicMock()
        mock_service_instance.get_section_headings.side_effect = Exception(
            "Unexpected error"
        )
        mock_service_class.return_value = mock_service_instance

        # Create request data
        request_data = {"article_title": "Apollo"}

        response = self.client.post(
            "/api/section-headings", data=request_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.data["error"], "An unexpected error occurred. Please try again."
        )


class TestResultViewDRF(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a real EditTask for testing
        self.edit_task = EditTask.objects.create(
            editing_mode="copyedit",
            article_title="Test Article",
            section_title="Test Section",
            llm_provider="google",
            status="PENDING",
        )
        self.task_id = str(self.edit_task.id)
        self.url = f"/api/results/{self.task_id}"

    def test_result_pending(self):
        # Task is already in PENDING state from setUp
        response = self.client.get(self.url)
        assert response.status_code == 202
        assert response.data["status"] == "PENDING"
        assert response.data["task_id"] == self.task_id

    def test_result_failure(self):
        self.edit_task.status = "FAILURE"
        self.edit_task.error_message = "fail error"
        self.edit_task.save()

        response = self.client.get(self.url)
        assert response.status_code == 500
        assert response.data["status"] == "FAILURE"
        assert response.data["task_id"] == self.task_id
        assert (
            "An unexpected error occurred. Please try again." in response.data["error"]
        )

    def test_result_success(self):
        self.edit_task.status = "SUCCESS"
        self.edit_task.result = {"paragraphs": ["foo"]}
        self.edit_task.save()

        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data["status"] == "SUCCESS"
        assert response.data["task_id"] == self.task_id
        assert response.data["result"] == {"paragraphs": ["foo"]}

    def test_result_success_with_error(self):
        self.edit_task.status = "SUCCESS"
        self.edit_task.result = {"error": "task error"}
        self.edit_task.save()

        response = self.client.get(self.url)
        assert response.status_code == 500
        assert response.data["status"] == "FAILURE"
        assert response.data["task_id"] == self.task_id
        assert (
            response.data["error"] == "An unexpected error occurred. Please try again."
        )

    def test_result_other_state(self):
        self.edit_task.status = "STARTED"
        self.edit_task.save()

        response = self.client.get(self.url)
        assert response.status_code == 202
        assert response.data["status"] == "STARTED"
        assert response.data["task_id"] == self.task_id

    def test_result_not_found(self):
        # Test with non-existent task ID
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f"/api/results/{fake_uuid}")
        assert response.status_code == 404

    def test_result_retry_state(self):
        # Test RETRY state (other states)
        self.edit_task.status = "RETRY"
        self.edit_task.save()

        response = self.client.get(self.url)
        assert response.status_code == 202
        assert response.data["status"] == "RETRY"
        assert response.data["task_id"] == self.task_id

    def test_result_pending_with_progress_data(self):
        # Test PENDING state with progress data
        self.edit_task.status = "PENDING"
        self.edit_task.progress_data = {"processed": 5, "total": 10}
        self.edit_task.save()

        response = self.client.get(self.url)
        assert response.status_code == 202
        assert response.data["status"] == "PENDING"
        assert response.data["task_id"] == self.task_id
        assert response.data["progress"] == {"processed": 5, "total": 10}


class TestEditTaskListViewDRF(TestCase):
    """Test EditTaskListView class using DRF testing patterns."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        # Create some test EditTasks
        now = datetime.now(timezone.utc)
        self.task1 = EditTask.objects.create(
            editing_mode="copyedit",
            status="SUCCESS",
            article_title="Test Article 1",
            section_title="Section 1",
            llm_provider="google",
            result={"paragraphs": [{"status": "CHANGED"}, {"status": "UNCHANGED"}]},
            created_at=now,
        )
        self.task2 = EditTask.objects.create(
            editing_mode="brevity",
            status="PENDING",
            article_title="Test Article 2",
            section_title="Section 2",
            llm_provider="openai",
            result=None,
            created_at=now,
        )

    def test_get_default_parameters(self):
        """Test GET request with default parameters."""
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("pagination", response.data)
        self.assertEqual(response.data["pagination"]["page"], 1)
        self.assertEqual(response.data["pagination"]["page_size"], 20)

    def test_get_with_pagination(self):
        """Test GET request with pagination parameters."""
        response = self.client.get("/api/tasks/?page=1&page_size=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["pagination"]["page"], 1)
        self.assertEqual(response.data["pagination"]["page_size"], 1)

    def test_get_with_status_filter(self):
        """Test GET request with status filter."""
        response = self.client.get("/api/tasks/?status=SUCCESS")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        success_tasks = [
            task for task in response.data["results"] if task["status"] == "SUCCESS"
        ]
        self.assertEqual(len(success_tasks), len(response.data["results"]))

    def test_get_with_editing_mode_filter(self):
        """Test GET request with editing_mode filter."""
        response = self.client.get("/api/tasks/?editing_mode=copyedit")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        copyedit_tasks = [
            task
            for task in response.data["results"]
            if task["editing_mode"] == "copyedit"
        ]
        self.assertEqual(len(copyedit_tasks), len(response.data["results"]))

    def test_get_with_date_filters(self):
        """Test GET request with date filters."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # YYYY-MM-DD format
        response = self.client.get(f"/api/tasks/?date_from={date_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_with_date_to_filter(self):
        """Test GET request with date_to filter."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # YYYY-MM-DD format
        response = self.client.get(f"/api/tasks/?date_to={date_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_with_invalid_date_from(self):
        """Test GET request with invalid date_from format."""
        response = self.client.get("/api/tasks/?date_from=invalid-date")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date_from format", response.data["error"])

    def test_get_with_invalid_date_to(self):
        """Test GET request with invalid date_to format."""
        response = self.client.get("/api/tasks/?date_to=invalid-date")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date_to format", response.data["error"])

    def test_calculate_changes_count_with_valid_result(self):
        """Test _calculate_changes_count with valid result."""
        from api.views.edit_views import EditTaskListView

        view = EditTaskListView()
        count = view._calculate_changes_count(self.task1)
        self.assertEqual(count, 1)  # One paragraph with status "CHANGED"

    def test_calculate_changes_count_with_no_result(self):
        """Test _calculate_changes_count with no result."""
        from api.views.edit_views import EditTaskListView

        view = EditTaskListView()
        count = view._calculate_changes_count(self.task2)
        self.assertIsNone(count)

    def test_calculate_changes_count_with_invalid_result(self):
        """Test _calculate_changes_count with invalid result format."""
        from api.views.edit_views import EditTaskListView

        now = datetime.now(timezone.utc)
        task = EditTask.objects.create(
            editing_mode="copyedit",
            status="SUCCESS",
            article_title="Test Article",
            section_title="Test Section",
            llm_provider="google",
            result="invalid string result",
            created_at=now,
        )
        view = EditTaskListView()
        count = view._calculate_changes_count(task)
        self.assertIsNone(count)

    def test_calculate_changes_count_with_no_paragraphs(self):
        """Test _calculate_changes_count with result but no paragraphs."""
        from api.views.edit_views import EditTaskListView

        now = datetime.now(timezone.utc)
        task = EditTask.objects.create(
            editing_mode="copyedit",
            status="SUCCESS",
            article_title="Test Article",
            section_title="Test Section",
            llm_provider="google",
            result={"other_data": "value"},
            created_at=now,
        )
        view = EditTaskListView()
        count = view._calculate_changes_count(task)
        self.assertIsNone(count)


class TestEditTaskDetailViewDRF(TestCase):
    """Test EditTaskDetailView class using DRF testing patterns."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        # Create a test EditTask
        self.task = EditTask.objects.create(
            editing_mode="copyedit",
            status="SUCCESS",
            article_title="Test Article",
            section_title="Test Section",
            llm_provider="google",
            llm_model="gemini-pro",
            result={"paragraphs": [{"status": "CHANGED", "content": "edited content"}]},
            error_message=None,
        )

    def test_get_existing_task(self):
        """Test GET request for an existing task."""
        response = self.client.get(f"/api/tasks/{self.task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["id"]), str(self.task.id))
        self.assertEqual(response.data["editing_mode"], "copyedit")
        self.assertEqual(response.data["status"], "SUCCESS")
        self.assertEqual(response.data["article_title"], "Test Article")
        self.assertEqual(response.data["section_title"], "Test Section")
        self.assertEqual(response.data["llm_provider"], "google")
        self.assertEqual(response.data["llm_model"], "gemini-pro")
        self.assertIn("result", response.data)
        self.assertIsNone(response.data["error_message"])

    def test_get_nonexistent_task(self):
        """Test GET request for a non-existent task."""
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(f"/api/tasks/{fake_uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestEditViewSerializerErrorHandling(TestCase):
    """Test edge cases for serializer error handling in EditView."""

    def setUp(self):
        self.client = APIClient()

    @patch("api.views.edit_views.EditRequestSerializer")
    def test_string_serializer_error_handling(self, mock_serializer_class):
        """Test serializer error handling when errors are strings."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Mock string error format
        mock_serializer.errors = {"article_title": "This is a string error"}
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/edit/copyedit", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("api.views.edit_views.EditRequestSerializer")
    def test_empty_errors_fallback_handling(self, mock_serializer_class):
        """Test serializer error handling when no field errors exist."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Mock empty errors dict
        mock_serializer.errors = {}
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/edit/copyedit", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid input data")

    @patch("api.views.edit_views.EditRequestSerializer")
    def test_exception_during_error_processing(self, mock_serializer_class):
        """Test exception handling during error message processing."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Create an object that will cause AttributeError when accessing .values() or similar
        mock_errors = MagicMock()
        mock_errors.values.side_effect = AttributeError("No values method")
        mock_serializer.errors = mock_errors
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/edit/copyedit", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid input data")

    @patch("api.views.edit_views.EditRequestSerializer")
    def test_empty_field_errors_fallback(self, mock_serializer_class):
        """Test fallback when field has no errors."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Mock field with non-list, non-string value
        mock_serializer.errors = {"field": None}
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/edit/copyedit", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid input data")


class TestSectionHeadingsViewSerializerErrorHandling(TestCase):
    """Test edge cases for serializer error handling in SectionHeadingsView."""

    def setUp(self):
        self.client = APIClient()

    @patch("api.views.edit_views.SectionHeadingsRequestSerializer")
    def test_string_serializer_error_handling(self, mock_serializer_class):
        """Test serializer error handling when errors are strings."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Mock string error format
        mock_serializer.errors = {"article_title": "This is a string error"}
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/section-headings", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("api.views.edit_views.SectionHeadingsRequestSerializer")
    def test_empty_errors_fallback_handling(self, mock_serializer_class):
        """Test serializer error handling when no field errors exist."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Mock empty errors dict
        mock_serializer.errors = {}
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/section-headings", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid input data")

    @patch("api.views.edit_views.SectionHeadingsRequestSerializer")
    def test_exception_during_error_processing(self, mock_serializer_class):
        """Test exception handling during error message processing."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Create an object that will cause AttributeError when accessing .values() or similar
        mock_errors = MagicMock()
        mock_errors.values.side_effect = AttributeError("No values method")
        mock_serializer.errors = mock_errors
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/section-headings", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid input data")

    @patch("api.views.edit_views.SectionHeadingsRequestSerializer")
    def test_empty_field_errors_fallback(self, mock_serializer_class):
        """Test fallback when field has no errors."""
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        # Mock field with non-list, non-string value
        mock_serializer.errors = {"field": None}
        mock_serializer_class.return_value = mock_serializer

        response = self.client.post("/api/section-headings", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid input data")


class TestEditTaskListViewPaginationErrorHandling(TestCase):
    """Test pagination error handling in EditTaskListView."""

    def setUp(self):
        self.client = APIClient()
        # Create a test task to ensure there's data
        EditTask.objects.create(
            editing_mode="copyedit",
            status="SUCCESS",
            article_title="Test Article",
            section_title="Test Section",
            llm_provider="google",
            result={"paragraphs": [{"status": "CHANGED"}]},
        )

    def test_page_not_integer_handling(self):
        """Test invalid page parameter handling."""
        response = self.client.get("/api/tasks/?page=invalid")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pagination"]["page"], 1)

    def test_empty_page_handling(self):
        """Test EmptyPage exception handling."""
        response = self.client.get("/api/tasks/?page=999")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return the last page (which would be page 1 with our single task)
        self.assertEqual(response.data["pagination"]["page"], 1)

    def test_invalid_page_size_handling(self):
        """Test invalid page_size parameter handling."""
        response = self.client.get("/api/tasks/?page_size=invalid")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["pagination"]["page_size"], 20
        )  # Default fallback

    @patch("django.core.paginator.Paginator")
    def test_paginator_page_not_integer_exception(self, mock_paginator_class):
        """Test PageNotAnInteger exception handling."""
        from unittest.mock import MagicMock

        from django.core.paginator import PageNotAnInteger

        # Mock paginator instance
        mock_paginator = MagicMock()
        mock_paginator_class.return_value = mock_paginator

        # Create a mock task object with all required attributes
        mock_task = MagicMock()
        mock_task.id = "test-id"
        mock_task.editing_mode = "copyedit"
        mock_task.status = "SUCCESS"
        mock_task.article_title = "Test Article"
        mock_task.section_title = "Test Section"
        mock_task.created_at = "2024-01-01T00:00:00Z"
        mock_task.completed_at = "2024-01-01T00:01:00Z"
        mock_task.llm_provider = "google"
        mock_task.llm_model = "gemini-pro"
        mock_task.result = {"paragraphs": [{"status": "CHANGED"}]}

        # Mock successful page object for fallback
        mock_page_obj = MagicMock()
        mock_page_obj.object_list = [mock_task]
        mock_page_obj.number = 1
        mock_page_obj.paginator.num_pages = 1
        mock_page_obj.paginator.count = 1
        mock_page_obj.has_next.return_value = False
        mock_page_obj.has_previous.return_value = False

        # First call raises PageNotAnInteger, second call succeeds
        mock_paginator.page.side_effect = [
            PageNotAnInteger("Page is not an integer"),
            mock_page_obj,
        ]

        response = self.client.get("/api/tasks/?page=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestResultViewErrorSanitization(TestCase):
    """Test error sanitization in ResultView."""

    def setUp(self):
        self.client = APIClient()

    def test_sanitize_error_message_empty_string(self):
        """Test _sanitize_error_message with empty string."""
        from api.views.edit_views import ResultView

        view = ResultView()
        result = view._sanitize_error_message("")
        self.assertEqual(result, "An error occurred during processing.")

    def test_sanitize_error_message_exception_during_sanitization(self):
        """Test _sanitize_error_message when ErrorSanitizer raises exception."""
        from api.views.edit_views import ResultView

        view = ResultView()

        # Mock ErrorSanitizer to raise an exception
        with patch(
            "api.views.edit_views.ErrorSanitizer.sanitize_exception"
        ) as mock_sanitizer:
            mock_sanitizer.side_effect = Exception("Sanitization failed")

            result = view._sanitize_error_message("Some error message")
            self.assertEqual(result, "An error occurred during processing.")
