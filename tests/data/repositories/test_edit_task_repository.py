"""Tests for EditTask repository."""

from uuid import uuid4

from django.test import TestCase

from data.models.edit_task import EditTask
from data.repositories.edit_task_repository import DjangoEditTaskRepository


class TestDjangoEditTaskRepository(TestCase):
    """Test Django EditTask repository implementation."""

    def setUp(self):
        """Set up test repository."""
        self.repository = DjangoEditTaskRepository()

    def test_create(self):
        """Test creating an EditTask."""
        task = self.repository.create(editing_mode="copyedit", content="Test content")
        self.assertIsInstance(task, EditTask)
        self.assertEqual(task.editing_mode, "copyedit")
        self.assertEqual(task.content, "Test content")

    def test_get_by_id(self):
        """Test getting an EditTask by ID."""
        task = EditTask.objects.create(editing_mode="copyedit")
        retrieved = self.repository.get_by_id(task.id)
        self.assertIsNotNone(retrieved)
        if retrieved is not None:
            self.assertEqual(retrieved.id, task.id)

    def test_get_by_id_not_found(self):
        """Test getting a non-existent EditTask."""
        result = self.repository.get_by_id(uuid4())
        self.assertIsNone(result)

    def test_get_by_celery_task_id(self):
        """Test getting an EditTask by Celery task ID."""
        celery_id = "test-celery-id"
        task = EditTask.objects.create(
            editing_mode="copyedit", celery_task_id=celery_id
        )
        retrieved = self.repository.get_by_celery_task_id(celery_id)
        self.assertIsNotNone(retrieved)
        if retrieved is not None:
            self.assertEqual(retrieved.id, task.id)

    def test_get_by_celery_task_id_not_found(self):
        """Test getting an EditTask by non-existent Celery task ID."""
        result = self.repository.get_by_celery_task_id("non-existent-celery-id")
        self.assertIsNone(result)

    def test_update(self):
        """Test updating an EditTask."""
        task = EditTask.objects.create(editing_mode="copyedit")
        updated = self.repository.update(task.id, status="SUCCESS")
        self.assertEqual(updated.status, "SUCCESS")

    def test_update_not_found(self):
        """Test updating a non-existent EditTask."""
        with self.assertRaises(EditTask.DoesNotExist):
            self.repository.update(uuid4(), status="SUCCESS")

    def test_delete(self):
        """Test deleting an EditTask."""
        task = EditTask.objects.create(editing_mode="copyedit")
        result = self.repository.delete(task.id)
        self.assertTrue(result)
        self.assertFalse(EditTask.objects.filter(id=task.id).exists())

    def test_delete_not_found(self):
        """Test deleting a non-existent EditTask."""
        result = self.repository.delete(uuid4())
        self.assertFalse(result)

    def test_list_all(self):
        """Test listing all EditTasks."""
        EditTask.objects.create(editing_mode="copyedit")
        EditTask.objects.create(editing_mode="brevity")
        queryset = self.repository.list_all()
        self.assertEqual(queryset.count(), 2)

    def test_list_by_status(self):
        """Test listing EditTasks by status."""
        EditTask.objects.create(editing_mode="copyedit", status="SUCCESS")
        EditTask.objects.create(editing_mode="brevity", status="PENDING")
        queryset = self.repository.list_by_status("SUCCESS")
        self.assertEqual(queryset.count(), 1)

    def test_list_paginated(self):
        """Test paginated listing of EditTasks."""
        for _i in range(5):
            EditTask.objects.create(editing_mode="copyedit")

        page = self.repository.list_paginated(page=1, page_size=2)
        self.assertEqual(len(page.object_list), 2)
        self.assertTrue(page.has_next())

    def test_list_paginated_with_filters(self):
        """Test paginated listing with filters."""
        EditTask.objects.create(editing_mode="copyedit", status="SUCCESS")
        EditTask.objects.create(editing_mode="brevity", status="PENDING")

        page = self.repository.list_paginated(
            filters={"status": "SUCCESS"}, page_size=10
        )
        self.assertEqual(len(page.object_list), 1)
