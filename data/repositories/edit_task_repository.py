from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet

from data.models import EditTask


class EditTaskRepositoryInterface(ABC):
    """Abstract interface for EditTask repository operations."""

    @abstractmethod
    def create(self, **kwargs) -> EditTask:
        """Create a new EditTask."""
        pass

    @abstractmethod
    def get_by_id(self, task_id: UUID) -> Optional[EditTask]:
        """Get an EditTask by its ID."""
        pass

    @abstractmethod
    def get_by_celery_task_id(self, celery_task_id: str) -> Optional[EditTask]:
        """Get an EditTask by its Celery task ID."""
        pass

    @abstractmethod
    def update(self, task_id: UUID, **kwargs) -> EditTask:
        """Update an EditTask."""
        pass

    @abstractmethod
    def delete(self, task_id: UUID) -> bool:
        """Delete an EditTask."""
        pass

    @abstractmethod
    def list_all(self) -> QuerySet[EditTask]:
        """Get all EditTasks."""
        pass

    @abstractmethod
    def list_by_status(self, status: str) -> QuerySet[EditTask]:
        """Get EditTasks by status."""
        pass

    @abstractmethod
    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Page:
        """Get paginated list of EditTasks with optional filters."""
        pass


class DjangoEditTaskRepository(EditTaskRepositoryInterface):
    """Django ORM implementation of EditTask repository."""

    def create(self, **kwargs) -> EditTask:
        """Create a new EditTask."""
        return EditTask.objects.create(**kwargs)

    def get_by_id(self, task_id: UUID) -> Optional[EditTask]:
        """Get an EditTask by its ID."""
        try:
            return EditTask.objects.get(id=task_id)
        except EditTask.DoesNotExist:
            return None

    def get_by_celery_task_id(self, celery_task_id: str) -> Optional[EditTask]:
        """Get an EditTask by its Celery task ID."""
        try:
            return EditTask.objects.get(celery_task_id=celery_task_id)
        except EditTask.DoesNotExist:
            return None

    def update(self, task_id: UUID, **kwargs) -> EditTask:
        """Update an EditTask."""
        task = self.get_by_id(task_id)
        if not task:
            raise EditTask.DoesNotExist(f"EditTask with id {task_id} does not exist")

        for key, value in kwargs.items():
            setattr(task, key, value)
        task.save()
        return task

    def delete(self, task_id: UUID) -> bool:
        """Delete an EditTask."""
        try:
            task = EditTask.objects.get(id=task_id)
            task.delete()
            return True
        except EditTask.DoesNotExist:
            return False

    def list_all(self) -> QuerySet[EditTask]:
        """Get all EditTasks."""
        return EditTask.objects.all()

    def list_by_status(self, status: str) -> QuerySet[EditTask]:
        """Get EditTasks by status."""
        return EditTask.objects.filter(status=status)

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Page:
        """Get paginated list of EditTasks with optional filters."""
        queryset = EditTask.objects.all()

        if filters:
            queryset = queryset.filter(**filters)

        paginator = Paginator(queryset, page_size)
        return paginator.get_page(page)
