import os
from datetime import datetime, timezone

# Configure Django settings before importing Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")

import django
from django.conf import settings
from django.core.paginator import Paginator
from django.test import TestCase

if not settings.configured:
    django.setup()

from api.exceptions.user_facing_exceptions import ValidationError
from data.models.edit_task import EditTask
from services.tasks.edit_task_query_service import EditTaskQueryService


class TestEditTaskQueryService(TestCase):
    """Test EditTaskQueryService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test tasks
        now = datetime.now(timezone.utc)
        self.task1 = EditTask.objects.create(
            editing_mode="copyedit",
            status="SUCCESS",
            article_title="Test Article 1",
            section_title="Section 1",
            content="Test content 1",
            llm_provider="google",
            result={"paragraphs": [{"status": "CHANGED"}, {"status": "UNCHANGED"}]},
            created_at=now,
        )
        self.task2 = EditTask.objects.create(
            editing_mode="brevity",
            status="PENDING",
            article_title="Test Article 2",
            section_title="Section 2",
            content="Test content 2",
            llm_provider="openai",
            result=None,
            created_at=now,
        )

    def test_parse_pagination_params_valid(self):
        """Test parsing valid pagination parameters."""
        page, page_size = EditTaskQueryService.parse_pagination_params("2", "10")
        self.assertEqual(page, 2)
        self.assertEqual(page_size, 10)

    def test_parse_pagination_params_defaults(self):
        """Test parsing pagination parameters with defaults."""
        page, page_size = EditTaskQueryService.parse_pagination_params(None, None)
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 20)

    def test_parse_pagination_params_invalid_page(self):
        """Test parsing invalid page parameter."""
        page, page_size = EditTaskQueryService.parse_pagination_params("invalid", "10")
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 10)

    def test_parse_pagination_params_invalid_page_size(self):
        """Test parsing invalid page_size parameter."""
        page, page_size = EditTaskQueryService.parse_pagination_params("1", "invalid")
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 20)

    def test_parse_pagination_params_page_size_max(self):
        """Test that page_size is capped at 100."""
        page, page_size = EditTaskQueryService.parse_pagination_params("1", "150")
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 100)

    def test_parse_iso_date_valid(self):
        """Test parsing valid ISO date string."""
        date_str = "2024-01-15"
        result = EditTaskQueryService.parse_iso_date(date_str)
        expected = datetime(2024, 1, 15, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_parse_iso_date_with_time(self):
        """Test parsing ISO date string with time."""
        date_str = "2024-01-15T10:30:00"
        result = EditTaskQueryService.parse_iso_date(date_str)
        expected = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_parse_iso_date_invalid(self):
        """Test parsing invalid ISO date string."""
        date_str = "invalid-date"
        with self.assertRaises(ValidationError) as cm:
            EditTaskQueryService.parse_iso_date(date_str)
        self.assertIn("Invalid date format", str(cm.exception))

    def test_parse_iso_date_with_field_name(self):
        """Test parsing ISO date with custom field name."""
        date_str = "invalid-date"
        with self.assertRaises(ValidationError) as cm:
            EditTaskQueryService.parse_iso_date(date_str, "date_from")
        self.assertIn("Invalid date_from format", str(cm.exception))

    def test_build_filtered_queryset_no_filters(self):
        """Test building queryset without filters."""
        queryset = EditTaskQueryService.build_filtered_queryset()
        self.assertEqual(queryset.count(), 2)

    def test_build_filtered_queryset_status_filter(self):
        """Test building queryset with status filter."""
        queryset = EditTaskQueryService.build_filtered_queryset(status_filter="SUCCESS")
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().status, "SUCCESS")

    def test_build_filtered_queryset_editing_mode_filter(self):
        """Test building queryset with editing mode filter."""
        queryset = EditTaskQueryService.build_filtered_queryset(
            editing_mode_filter="brevity"
        )
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().editing_mode, "brevity")

    def test_build_filtered_queryset_date_from_filter(self):
        """Test building queryset with date_from filter."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        queryset = EditTaskQueryService.build_filtered_queryset(date_from=date_str)
        self.assertEqual(queryset.count(), 2)

    def test_build_filtered_queryset_date_to_filter(self):
        """Test building queryset with date_to filter."""
        # Use a date that's after the tasks were created
        future_date = datetime.now(timezone.utc).replace(
            year=2100, hour=23, minute=59, second=59, microsecond=999999
        )
        date_str = future_date.strftime("%Y-%m-%d")
        queryset = EditTaskQueryService.build_filtered_queryset(date_to=date_str)
        self.assertEqual(queryset.count(), 2)

    def test_build_filtered_queryset_invalid_date(self):
        """Test building queryset with invalid date filter."""
        with self.assertRaises(ValidationError) as cm:
            EditTaskQueryService.build_filtered_queryset(date_from="invalid-date")
        self.assertIn("Invalid date_from format", str(cm.exception))

    def test_paginate_queryset_valid_page(self):
        """Test paginating queryset with valid page."""
        queryset = EditTask.objects.all()
        page_obj = EditTaskQueryService.paginate_queryset(queryset, 1, 1)
        self.assertEqual(page_obj.number, 1)
        self.assertEqual(len(page_obj.object_list), 1)

    def test_paginate_queryset_page_not_integer(self):
        """Test paginating queryset with non-integer page."""
        queryset = EditTask.objects.all()
        # Passing 0 as page returns the last page, which is page 2 with 2 items and page size 1
        page_obj = EditTaskQueryService.paginate_queryset(queryset, 0, 1)
        self.assertEqual(page_obj.number, 2)

    def test_paginate_queryset_page_string_not_integer(self):
        """Test paginating queryset with string that is not an integer."""
        queryset = EditTask.objects.all()
        # Passing "invalid" as page should trigger PageNotAnInteger exception
        page_obj = EditTaskQueryService.paginate_queryset(queryset, "invalid", 1)
        self.assertEqual(page_obj.number, 1)

    def test_paginate_queryset_empty_page(self):
        """Test paginating queryset with empty page."""
        queryset = EditTask.objects.all()
        page_obj = EditTaskQueryService.paginate_queryset(queryset, 999, 1)
        self.assertEqual(
            page_obj.number, 2
        )  # Should return last page (page 2 with 2 items, page size 1)

    def test_calculate_changes_count_valid_result(self):
        """Test calculating changes count with valid result."""
        count = EditTaskQueryService.calculate_changes_count(self.task1)
        self.assertEqual(count, 1)

    def test_calculate_changes_count_no_result(self):
        """Test calculating changes count with no result."""
        count = EditTaskQueryService.calculate_changes_count(self.task2)
        self.assertIsNone(count)

    def test_calculate_changes_count_invalid_result(self):
        """Test calculating changes count with invalid result format."""
        self.task1.result = "invalid string"
        count = EditTaskQueryService.calculate_changes_count(self.task1)
        self.assertIsNone(count)

    def test_calculate_changes_count_no_paragraphs(self):
        """Test calculating changes count with result but no paragraphs."""
        self.task1.result = {"other_data": "value"}
        count = EditTaskQueryService.calculate_changes_count(self.task1)
        self.assertIsNone(count)

    def test_serialize_task_list(self):
        """Test serializing task list."""
        queryset = EditTask.objects.all()
        paginator = Paginator(queryset, 10)
        page_obj = paginator.page(1)

        serialized = EditTaskQueryService.serialize_task_list(page_obj)
        self.assertEqual(len(serialized), 2)

        # Check that we have the expected tasks (order may vary)
        task_ids = [task["id"] for task in serialized]
        self.assertIn(self.task1.id, task_ids)
        self.assertIn(self.task2.id, task_ids)

        # Find the task1 data
        task1_data = next(task for task in serialized if task["id"] == self.task1.id)
        self.assertEqual(task1_data["editing_mode"], "copyedit")
        self.assertEqual(task1_data["status"], "SUCCESS")
        self.assertEqual(task1_data["article_title"], "Test Article 1")
        self.assertEqual(task1_data["section_title"], "Section 1")
        self.assertEqual(task1_data["llm_provider"], "google")
        self.assertIn("changes_count", task1_data)

    def test_build_paginated_response(self):
        """Test building paginated response."""
        queryset = EditTask.objects.all()
        paginator = Paginator(queryset, 10)
        page_obj = paginator.page(1)

        response = EditTaskQueryService.build_paginated_response(page_obj, 10)

        self.assertIn("results", response)
        self.assertIn("pagination", response)
        self.assertEqual(len(response["results"]), 2)
        self.assertEqual(response["pagination"]["page"], 1)
        self.assertEqual(response["pagination"]["page_size"], 10)
        self.assertEqual(response["pagination"]["total_count"], 2)
        self.assertEqual(response["pagination"]["total_pages"], 1)
        self.assertFalse(response["pagination"]["has_next"])
        self.assertFalse(response["pagination"]["has_previous"])

    def test_get_filtered_and_paginated_tasks(self):
        """Test complete workflow for getting filtered and paginated tasks."""
        response = EditTaskQueryService.get_filtered_and_paginated_tasks(
            page_param="1", page_size_param="10", status_filter="SUCCESS"
        )

        self.assertIn("results", response)
        self.assertIn("pagination", response)
        self.assertEqual(len(response["results"]), 1)
        self.assertEqual(response["results"][0]["status"], "SUCCESS")

    def test_get_filtered_and_paginated_tasks_with_date_filter(self):
        """Test getting filtered and paginated tasks with date filter."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = EditTaskQueryService.get_filtered_and_paginated_tasks(
            page_param="1", page_size_param="10", date_from=date_str
        )

        self.assertIn("results", response)
        self.assertIn("pagination", response)
        self.assertEqual(len(response["results"]), 2)

    def test_get_filtered_and_paginated_tasks_invalid_date(self):
        """Test getting filtered and paginated tasks with invalid date."""
        with self.assertRaises(ValidationError) as cm:
            EditTaskQueryService.get_filtered_and_paginated_tasks(
                page_param="1", page_size_param="10", date_from="invalid-date"
            )
        self.assertIn("Invalid date_from format", str(cm.exception))
