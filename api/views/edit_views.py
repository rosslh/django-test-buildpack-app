from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import (
    ErrorSanitizer,
    ValidationError,
)
from api.serializers.edit_serializers import (
    EditRequestSerializer,
    EditResponseSerializer,
    EditTaskDetailSerializer,
    EditTaskListSerializer,
    SectionHeadingsRequestSerializer,
    SectionHeadingsResponseSerializer,
)
from data.models.edit_task import EditTask
from services.tasks.edit_task_query_service import EditTaskQueryService
from services.tasks.edit_task_service import EditTaskService
from services.utils.section_headings_service import SectionHeadingsService

# Common API responses for OpenAPI documentation
COMMON_API_RESPONSES = {
    400: {"description": "Bad Request - Invalid input parameters"},
    401: {"description": "Unauthorized - API key required"},
    404: {"description": "Not Found - Article or section not found"},
    500: {"description": "Server Error - Internal processing error"},
}


@extend_schema_view(
    post=extend_schema(
        summary="AI-Powered Wikipedia Section and Content Editing",
        description="Use advanced AI to edit specific sections of Wikipedia articles. Provide an article title with a section title to fetch and edit that specific section from Wikipedia. Select 'brevity' mode to shorten text or 'copyedit' mode to improve grammar, style, and clarity. The system preserves formatting, protects links and references, maintains factual accuracy, and automatically retains regional spelling. Returns a task_id which can be used to poll for results.",
        request=EditRequestSerializer,
        responses={202: {"description": "Task accepted and processing"}},
        parameters=[
            OpenApiParameter(
                name="editing_mode",
                location=OpenApiParameter.PATH,
                description="The editing mode to apply: 'brevity' for conciseness improvements, 'copyedit' for comprehensive editorial enhancements",
                required=True,
                type=OpenApiTypes.STR,
                enum=["brevity", "copyedit"],
            ),
            OpenApiParameter(
                name="X-Google-API-Key",
                location=OpenApiParameter.HEADER,
                description="Google API key for using Gemini models",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="X-OpenAI-API-Key",
                location=OpenApiParameter.HEADER,
                description="OpenAI API key for using GPT models",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="X-Anthropic-API-Key",
                location=OpenApiParameter.HEADER,
                description="Anthropic API key for using Claude models",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="X-Mistral-API-Key",
                location=OpenApiParameter.HEADER,
                description="Mistral API key for using Mistral models",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="X-Perplexity-API-Key",
                location=OpenApiParameter.HEADER,
                description="Perplexity API key for using Perplexity models",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        tags=["Wiki Editing"],
    )
)
@method_decorator(ratelimit(key="ip", rate="100/h", block=True), name="dispatch")
class EditView(APIView):
    """API endpoint for editing specific Wikipedia article sections using AI.

    Provide article_title and section_title to fetch and edit a specific section of a Wikipedia article.

    Supports two editing modes:
    - brevity: Makes content more concise
    - copyedit: Improves grammar, style, and clarity

    Returns a task_id which can be used to poll for results.
    """

    def post(self, request, *args, **kwargs):
        editing_mode = kwargs.get("editing_mode")

        if editing_mode not in ["brevity", "copyedit"]:
            raise ValidationError(
                f"Invalid editing mode '{editing_mode}'. Must be 'brevity' or 'copyedit'."
            )

        serializer = EditRequestSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(self._extract_serializer_error(serializer))

        article_title = serializer.validated_data.get("article_title")
        section_title = serializer.validated_data.get("section_title")

        # Get API keys from headers
        google_api_key = request.META.get("HTTP_X_GOOGLE_API_KEY")
        openai_api_key = request.META.get("HTTP_X_OPENAI_API_KEY")
        anthropic_api_key = request.META.get("HTTP_X_ANTHROPIC_API_KEY")
        mistral_api_key = request.META.get("HTTP_X_MISTRAL_API_KEY")
        perplexity_api_key = request.META.get("HTTP_X_PERPLEXITY_API_KEY")

        # Use EditTaskService to handle the complete workflow
        result = EditTaskService.create_and_start_edit_task(
            editing_mode=editing_mode,
            article_title=article_title,
            section_title=section_title,
            google_api_key=google_api_key,
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
            mistral_api_key=mistral_api_key,
            perplexity_api_key=perplexity_api_key,
        )

        return Response(result, status=status.HTTP_202_ACCEPTED)

    def _extract_serializer_error(self, serializer):
        """Safely extract error messages from serializer errors with proper fallback handling."""
        try:
            # Try to get the first error message from the first field
            if serializer.errors:
                # Get the first field with errors
                first_field_errors = next(iter(serializer.errors.values()))
                if isinstance(first_field_errors, list) and first_field_errors:
                    error_message = str(first_field_errors[0])
                elif isinstance(first_field_errors, str):
                    error_message = first_field_errors
                else:
                    error_message = "Invalid input data"
            else:
                error_message = "Invalid input data"
        except (StopIteration, AttributeError, TypeError):
            # Fallback if the error structure is unexpected
            error_message = "Invalid input data"

        return error_message


@extend_schema_view(
    get=extend_schema(
        summary="Get Task Results",
        description="Retrieve the results of an editing task by its task ID. The response will include the status of the task and, if completed, the editing results.",
        responses={
            200: EditResponseSerializer,
            202: {"description": "Task is still processing"},
            404: {"description": "Task not found"},
            500: {"description": "Server Error - Internal processing error"},
        },
        tags=["Wiki Editing"],
    )
)
class ResultView(APIView):
    """API endpoint for retrieving the results of an editing task."""

    def get(self, request, task_id, *args, **kwargs):
        # Get the EditTask from database
        edit_task = get_object_or_404(EditTask, id=task_id)

        if edit_task.status == "PENDING" or edit_task.status == "STARTED":
            # Task is still processing
            response_data = {"task_id": task_id, "status": edit_task.status}
            # Use the new method that handles both legacy and enhanced progress formats
            progress_data = edit_task.get_progress_for_api()
            if progress_data:
                response_data["progress"] = progress_data
            return Response(
                response_data,
                status=status.HTTP_202_ACCEPTED,
            )
        elif edit_task.status == "FAILURE":
            # Task failed - sanitize the error message
            sanitized_error = self._sanitize_error_message(edit_task.error_message)
            return Response(
                {
                    "task_id": task_id,
                    "status": "FAILURE",
                    "error": sanitized_error,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        elif edit_task.status == "SUCCESS":
            # Task completed successfully
            result = edit_task.result

            # Check if there was an error during task execution
            if isinstance(result, dict) and "error" in result:
                sanitized_error = self._sanitize_error_message(result["error"])
                return Response(
                    {"task_id": task_id, "status": "FAILURE", "error": sanitized_error},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Return the successful result
            response_data = {"task_id": task_id, "status": "SUCCESS", "result": result}
            return Response(response_data)
        else:
            # Task is in some other state (e.g., RETRY, REVOKED)
            return Response(
                {"task_id": task_id, "status": edit_task.status},
                status=status.HTTP_202_ACCEPTED,
            )

    def _sanitize_error_message(self, error_message: str) -> str:
        """Sanitize error message to prevent information leakage."""
        if not error_message:
            return "An error occurred during processing."

        try:
            # Create a mock exception to leverage our sanitization logic
            mock_exception = Exception(error_message)
            sanitized_error = ErrorSanitizer.sanitize_exception(mock_exception)
            return sanitized_error.user_message
        except Exception:
            # If sanitization fails, return a safe default message
            return "An error occurred during processing."


@extend_schema_view(
    post=extend_schema(
        summary="Retrieve Level 2 Section Headings from Wikipedia Article",
        description="Retrieve all level 2 section headings (== Section ==) from a Wikipedia article. This endpoint fetches the article content and extracts only the main section headings. Returns a structured list of level 2 section headings.",
        request=SectionHeadingsRequestSerializer,
        responses={200: SectionHeadingsResponseSerializer, **COMMON_API_RESPONSES},
        tags=["Wiki Editing"],
    )
)
class SectionHeadingsView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.section_headings_service = SectionHeadingsService()

    def post(self, request, *args, **kwargs):
        serializer = SectionHeadingsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(self._extract_serializer_error(serializer))

        article_title = serializer.validated_data.get("article_title")

        if not article_title:
            raise ValidationError("Article title must be provided")

        response_data = self.section_headings_service.get_section_headings(
            article_title
        )
        return Response(response_data)

    def _extract_serializer_error(self, serializer):
        """Safely extract error messages from serializer errors with proper fallback handling."""
        try:
            # Try to get the first error message from the first field
            if serializer.errors:
                # Get the first field with errors
                first_field_errors = next(iter(serializer.errors.values()))
                if isinstance(first_field_errors, list) and first_field_errors:
                    error_message = str(first_field_errors[0])
                elif isinstance(first_field_errors, str):
                    error_message = first_field_errors
                else:
                    error_message = "Invalid input data"
            else:
                error_message = "Invalid input data"
        except (StopIteration, AttributeError, TypeError):
            # Fallback if the error structure is unexpected
            error_message = "Invalid input data"

        return error_message


@extend_schema_view(
    get=extend_schema(
        summary="List Edit Tasks",
        description="Retrieve a paginated list of edit tasks with basic information. Supports filtering by status, editing mode, and date range.",
        responses={200: EditTaskListSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="page",
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="page_size",
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 20, max: 100)",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                description="Filter by task status",
                required=False,
                type=OpenApiTypes.STR,
                enum=["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED"],
            ),
            OpenApiParameter(
                name="editing_mode",
                location=OpenApiParameter.QUERY,
                description="Filter by editing mode",
                required=False,
                type=OpenApiTypes.STR,
                enum=["copyedit", "brevity"],
            ),
            OpenApiParameter(
                name="date_from",
                location=OpenApiParameter.QUERY,
                description="Filter tasks created after this date (ISO format)",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="date_to",
                location=OpenApiParameter.QUERY,
                description="Filter tasks created before this date (ISO format)",
                required=False,
                type=OpenApiTypes.DATE,
            ),
        ],
        tags=["Edit History"],
    )
)
class EditTaskListView(APIView):
    """API endpoint for listing edit tasks with pagination and filtering."""

    def get(self, request, *args, **kwargs):
        response_data = EditTaskQueryService.get_filtered_and_paginated_tasks(
            page_param=request.query_params.get("page"),
            page_size_param=request.query_params.get("page_size"),
            status_filter=request.query_params.get("status"),
            editing_mode_filter=request.query_params.get("editing_mode"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(response_data, status=status.HTTP_200_OK)

    def _calculate_changes_count(self, task):
        """Calculate the number of changed paragraphs in a task result."""
        if not task.result:
            return None

        if not isinstance(task.result, dict):
            return None

        paragraphs = task.result.get("paragraphs")
        if not paragraphs:
            return None

        changed_count = 0
        for paragraph in paragraphs:
            if isinstance(paragraph, dict) and paragraph.get("status") == "CHANGED":
                changed_count += 1

        return changed_count


@extend_schema_view(
    get=extend_schema(
        summary="Get Edit Task Details",
        description="Retrieve detailed information about a specific edit task including complete results.",
        responses={
            200: EditTaskDetailSerializer,
            404: {"description": "Task not found"},
        },
        tags=["Edit History"],
    )
)
class EditTaskDetailView(APIView):
    """API endpoint for retrieving detailed information about a specific edit task."""

    def get(self, request, task_id, *args, **kwargs):
        # Get the EditTask from database
        edit_task = get_object_or_404(EditTask, id=task_id)

        # Serialize the task with complete details
        task_data = {
            "id": edit_task.id,
            "editing_mode": edit_task.editing_mode,
            "status": edit_task.status,
            "article_title": edit_task.article_title,
            "section_title": edit_task.section_title,
            "created_at": edit_task.created_at,
            "started_at": edit_task.started_at,
            "completed_at": edit_task.completed_at,
            "llm_provider": edit_task.llm_provider,
            "llm_model": edit_task.llm_model,
            "result": edit_task.result,
            "error_message": edit_task.error_message,
        }

        return Response(task_data)
