import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class EditTask(models.Model):
    """Model to store edit task information and results in database."""

    # Task identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Celery task ID for background processing",
    )

    # Task metadata
    editing_mode = models.CharField(
        max_length=50, help_text="Edit mode: copyedit, brevity, etc."
    )

    # Input data
    content = models.TextField(
        null=True, blank=True, help_text="Raw wikitext content to edit"
    )
    article_title = models.CharField(
        max_length=500, null=True, blank=True, help_text="Wikipedia article title"
    )
    section_title = models.CharField(
        max_length=500, null=True, blank=True, help_text="Wikipedia section title"
    )

    # LLM configuration
    llm_provider = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="LLM provider: google, openai, etc.",
    )
    llm_model = models.CharField(
        max_length=100, null=True, blank=True, help_text="Specific model used"
    )

    # Task status
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("STARTED", "Started"),
        ("SUCCESS", "Success"),
        ("FAILURE", "Failure"),
        ("RETRY", "Retry"),
        ("REVOKED", "Revoked"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    # Results
    result = models.JSONField(null=True, blank=True, help_text="Edit results as JSON")
    progress_data = models.JSONField(
        null=True, blank=True, help_text="Progress tracking data during processing"
    )
    error_message = models.TextField(
        null=True, blank=True, help_text="Error message if task failed"
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When task processing started"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When task completed"
    )

    # Optional tracking fields
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who initiated the task (if authenticated)",
    )

    class Meta:
        db_table = "edit_tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def __str__(self):
        return f"EditTask {self.id} - {self.editing_mode} - {self.status}"

    def is_completed(self):
        """Check if task is in a completed state (success or failure)."""
        return self.status in ["SUCCESS", "FAILURE", "REVOKED"]

    def is_processing(self):
        """Check if task is currently being processed."""
        return self.status in ["PENDING", "STARTED", "RETRY"]

    def mark_started(self):
        """Mark task as started."""
        self.status = "STARTED"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def mark_success(self, result_data):
        """Mark task as successfully completed with results."""
        self.status = "SUCCESS"
        self.result = result_data
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "result", "completed_at", "updated_at"])

    def mark_failure(self, error_message):
        """Mark task as failed with error message."""
        self.status = "FAILURE"
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(
            update_fields=["status", "error_message", "completed_at", "updated_at"]
        )

    def update_progress_enhanced(self, progress_data):
        """Update progress data with enhanced granular phase tracking.

        Args:
            progress_data: Dictionary containing enhanced progress information with format:
            {
                "total_paragraphs": int,
                "progress_percentage": int,
                "phase_counts": {
                    "pending": int,
                    "pre_processing": int,
                    "llm_processing": int,
                    "post_processing": int,
                    "complete": int
                },
                "paragraphs": [
                    {
                        "index": int,
                        "phase": str,
                        "content_preview": str,
                        "status": str,  # Only set when phase is "complete"
                        "started_at": str,  # ISO timestamp
                        "completed_at": str,  # ISO timestamp, only when complete
                    }
                ]
            }
        """
        # Validate that phase_counts sum to total_paragraphs
        if "phase_counts" in progress_data and "total_paragraphs" in progress_data:
            total_in_phases = sum(progress_data["phase_counts"].values())
            if total_in_phases != progress_data["total_paragraphs"]:
                raise ValueError(
                    f"Phase counts ({total_in_phases}) don't match total paragraphs ({progress_data['total_paragraphs']})"
                )

        self.progress_data = progress_data
        self.save(update_fields=["progress_data", "updated_at"])

    def get_progress_for_api(self):
        """Get progress data formatted for API response.

        Returns:
            Dictionary containing progress data. If enhanced progress is available,
            returns enhanced format. Otherwise returns legacy format.
        """
        if not self.progress_data:
            return None

        return self.progress_data
