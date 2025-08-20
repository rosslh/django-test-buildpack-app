from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class HealthCheckView(APIView):
    """Simple health check endpoint for the API."""
    
    def get(self, request):
        return Response(
            {"status": "healthy", "message": "EditEngine API is running"},
            status=status.HTTP_200_OK
        )


class EditView(APIView):
    """Simplified edit endpoint without database."""
    
    def post(self, request, editing_mode):
        # For now, return a mock response
        return Response(
            {
                "task_id": "mock-task-123",
                "status": "accepted",
                "editing_mode": editing_mode,
                "message": "Edit request received (mock response)"
            },
            status=status.HTTP_202_ACCEPTED
        )


class ResultView(APIView):
    """Simplified result endpoint without database."""
    
    def get(self, request, task_id):
        # For now, return a mock response
        return Response(
            {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "result": {
                    "message": "Mock result for testing deployment"
                }
            },
            status=status.HTTP_200_OK
        )


class SectionHeadingsView(APIView):
    """Simplified section headings endpoint."""
    
    def post(self, request):
        # For now, return a mock response
        return Response(
            {
                "article_title": request.data.get("article_title", "Unknown"),
                "headings": ["Introduction", "History", "References"]
            },
            status=status.HTTP_200_OK
        )