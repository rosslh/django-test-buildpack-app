from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import QuerySet

from api.exceptions import ValidationError
from data.models.edit_task import EditTask


class EditTaskQueryService:
    """Service for handling EditTask querying, filtering, and pagination."""

    @staticmethod
    def parse_pagination_params(
        page_param: Optional[str], page_size_param: Optional[str]
    ) -> Tuple[int, int]:
        """Extract and validate pagination parameters.

        Args:
            page_param: Page number as string
            page_size_param: Page size as string

        Returns:
            Tuple of (page, page_size) with validated values
        """
        try:
            page = int(page_param) if page_param else 1
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = min(int(page_size_param) if page_size_param else 20, 100)
        except (ValueError, TypeError):
            page_size = 20

        return page, page_size

    @staticmethod
    def parse_iso_date(date_string: str, field_name: str = "date") -> datetime:
        """Parse ISO date string and return timezone-aware datetime object.

        Args:
            date_string: ISO format date string
            field_name: Name of the field for error messages

        Returns:
            datetime object with UTC timezone

        Raises:
            ValueError: If date string is not in valid ISO format
        """
        try:
            return datetime.fromisoformat(date_string).replace(tzinfo=timezone.utc)
        except ValueError as err:
            raise ValidationError(f"Invalid {field_name} format") from err

    @staticmethod
    def build_filtered_queryset(
        status_filter: Optional[str] = None,
        editing_mode_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> QuerySet:
        """Build queryset with applied filters.

        Args:
            status_filter: Filter by task status
            editing_mode_filter: Filter by editing mode
            date_from: Filter tasks created after this date (ISO format)
            date_to: Filter tasks created before this date (ISO format)

        Returns:
            Filtered QuerySet of EditTask objects

        Raises:
            ValueError: If date filters are not in valid ISO format
        """
        queryset = EditTask.objects.all()

        # Apply basic filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if editing_mode_filter:
            queryset = queryset.filter(editing_mode=editing_mode_filter)

        # Apply date filters
        if date_from:
            date_from_obj = EditTaskQueryService.parse_iso_date(date_from, "date_from")
            queryset = queryset.filter(created_at__gte=date_from_obj)

        if date_to:
            date_to_obj = EditTaskQueryService.parse_iso_date(date_to, "date_to")
            queryset = queryset.filter(created_at__lte=date_to_obj)

        return queryset

    @staticmethod
    def paginate_queryset(queryset: QuerySet, page: Union[int, str], page_size: int):
        """Apply pagination to queryset.

        Args:
            queryset: QuerySet to paginate
            page: Page number
            page_size: Number of items per page

        Returns:
            Paginated page object
        """
        paginator = Paginator(queryset, page_size)

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        return page_obj

    @staticmethod
    def calculate_changes_count(task: EditTask) -> Optional[int]:
        """Calculate the number of changed paragraphs from task results.

        Args:
            task: EditTask instance

        Returns:
            Number of changed paragraphs or None if not available
        """
        if not task.result or not isinstance(task.result, dict):
            return None

        paragraphs = task.result.get("paragraphs", [])
        if not paragraphs:
            return None

        changed_count = sum(
            1 for paragraph in paragraphs if paragraph.get("status") == "CHANGED"
        )
        return changed_count

    @staticmethod
    def serialize_task_list(page_obj) -> List[Dict[str, Any]]:
        """Serialize a list of EditTask objects for API response.

        Args:
            page_obj: Paginated page object containing EditTask instances

        Returns:
            List of serialized task data dictionaries
        """
        serialized_tasks = []
        for task in page_obj.object_list:
            task_data = {
                "id": task.id,
                "editing_mode": task.editing_mode,
                "status": task.status,
                "article_title": task.article_title,
                "section_title": task.section_title,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "llm_provider": task.llm_provider,
                "llm_model": task.llm_model,
                "changes_count": EditTaskQueryService.calculate_changes_count(task),
            }
            serialized_tasks.append(task_data)
        return serialized_tasks

    @staticmethod
    def build_paginated_response(page_obj, page_size: int) -> Dict[str, Any]:
        """Build the complete paginated response data.

        Args:
            page_obj: Paginated page object
            page_size: Number of items per page

        Returns:
            Complete response data with results and pagination info
        """
        serialized_tasks = EditTaskQueryService.serialize_task_list(page_obj)

        response_data = {
            "results": serialized_tasks,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total_count": page_obj.paginator.count,
                "total_pages": page_obj.paginator.num_pages,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }

        return response_data

    @classmethod
    def get_filtered_and_paginated_tasks(
        cls,
        page_param: Optional[str] = None,
        page_size_param: Optional[str] = None,
        status_filter: Optional[str] = None,
        editing_mode_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete workflow to get filtered and paginated edit tasks.

        Args:
            page_param: Page number as string
            page_size_param: Page size as string
            status_filter: Filter by task status
            editing_mode_filter: Filter by editing mode
            date_from: Filter tasks created after this date (ISO format)
            date_to: Filter tasks created before this date (ISO format)

        Returns:
            Complete response data with filtered and paginated tasks

        Raises:
            ValueError: If date filters are not in valid ISO format
        """
        # Parse pagination parameters
        page, page_size = cls.parse_pagination_params(page_param, page_size_param)

        # Build filtered queryset
        queryset = cls.build_filtered_queryset(
            status_filter=status_filter,
            editing_mode_filter=editing_mode_filter,
            date_from=date_from,
            date_to=date_to,
        )

        # Apply pagination
        page_obj = cls.paginate_queryset(queryset, page, page_size)

        # Build and return response
        return cls.build_paginated_response(page_obj, page_size)
