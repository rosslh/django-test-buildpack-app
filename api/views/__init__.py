from api.views.edit_views import (
    EditTaskDetailView,
    EditTaskListView,
    EditView,
    ResultView,
    SectionHeadingsView,
)

# Keep the existing health check for compatibility
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class HealthCheckView(APIView):
    """Simple health check endpoint for the API."""

    def get(self, request):
        return Response(
            {"status": "healthy", "message": "EditEngine API is running"},
            status=status.HTTP_200_OK,
        )


__all__ = [
    "EditTaskDetailView",
    "EditTaskListView",
    "EditView",
    "ResultView",
    "SectionHeadingsView",
    "HealthCheckView",
]
