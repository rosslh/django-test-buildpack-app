from typing import Any, Dict, Optional

from api.exceptions import APIKeyError
from data.models.edit_task import EditTask
from services.security.encryption_service import EncryptionService
from services.tasks.edit_tasks import process_edit_task_batched


class EditTaskService:
    """Service for handling EditTask creation, management, and business logic."""

    @staticmethod
    def create_llm_config(
        google_api_key: Optional[str],
        openai_api_key: Optional[str],
        anthropic_api_key: Optional[str],
        mistral_api_key: Optional[str],
        perplexity_api_key: Optional[str],
    ) -> Dict[str, str]:
        """Create a configuration dictionary for the LLM to be used in the task."""
        if google_api_key:
            return {"provider": "google", "api_key": google_api_key}
        elif openai_api_key:
            return {"provider": "openai", "api_key": openai_api_key}
        elif anthropic_api_key:
            return {"provider": "anthropic", "api_key": anthropic_api_key}
        elif mistral_api_key:
            return {"provider": "mistral", "api_key": mistral_api_key}
        elif perplexity_api_key:
            return {"provider": "perplexity", "api_key": perplexity_api_key}
        else:
            raise APIKeyError()

    @staticmethod
    def validate_api_keys(
        google_api_key: Optional[str],
        openai_api_key: Optional[str],
        anthropic_api_key: Optional[str],
        mistral_api_key: Optional[str],
        perplexity_api_key: Optional[str],
    ) -> bool:
        """Validate that at least one API key is provided."""
        return bool(
            google_api_key
            or openai_api_key
            or anthropic_api_key
            or mistral_api_key
            or perplexity_api_key
        )

    @staticmethod
    def create_edit_task(
        editing_mode: str,
        article_title: str,
        section_title: str,
        llm_config: Dict[str, Any],
    ) -> EditTask:
        """Create a new EditTask record in the database."""
        return EditTask.objects.create(
            editing_mode=editing_mode,
            article_title=article_title,
            section_title=section_title,
            llm_provider=llm_config.get("provider"),
            llm_model=llm_config.get("model"),
        )

    @staticmethod
    def build_task_kwargs(
        edit_task_id: str,
        article_title: str,
        section_title: str,
    ) -> Dict[str, Any]:
        """Build task parameters for the Celery task."""
        return {
            "edit_task_id": edit_task_id,
            "article_title": article_title,
            "section_title": section_title,
        }

    @staticmethod
    def start_processing_task(
        editing_mode: str, llm_config: Dict[str, Any], task_kwargs: Dict[str, Any]
    ) -> str:
        """Start processing the edit task asynchronously and return the Celery task ID."""
        # Encrypt the llm_config to secure API keys in transit
        encryption_service = EncryptionService()
        encrypted_config = encryption_service.encrypt_dict(llm_config)

        celery_task = process_edit_task_batched.delay(
            editing_mode=editing_mode, encrypted_llm_config=encrypted_config, **task_kwargs
        )
        return celery_task.id

    @staticmethod
    def update_task_with_celery_id(edit_task: EditTask, celery_task_id: str) -> None:
        """Update the EditTask with the Celery task ID."""
        edit_task.celery_task_id = celery_task_id
        edit_task.save(update_fields=["celery_task_id"])

    @classmethod
    def create_and_start_edit_task(
        cls,
        editing_mode: str,
        article_title: str,
        section_title: str,
        google_api_key: Optional[str],
        openai_api_key: Optional[str],
        anthropic_api_key: Optional[str],
        mistral_api_key: Optional[str],
        perplexity_api_key: Optional[str],
    ) -> Dict[str, Any]:
        """Complete workflow to create and start an edit task.

        Returns:
            Dict containing task_id and status_url

        Raises:
            ValueError: If no valid API key is provided
        """
        # Validate API keys
        if not cls.validate_api_keys(
            google_api_key,
            openai_api_key,
            anthropic_api_key,
            mistral_api_key,
            perplexity_api_key,
        ):
            raise APIKeyError(
                "API key required. Provide one of: X-Google-API-Key, X-OpenAI-API-Key, X-Anthropic-API-Key, X-Mistral-API-Key, or X-Perplexity-API-Key header"
            )

        # Create LLM configuration
        llm_config = cls.create_llm_config(
            google_api_key,
            openai_api_key,
            anthropic_api_key,
            mistral_api_key,
            perplexity_api_key,
        )

        # Create EditTask record
        edit_task = cls.create_edit_task(
            editing_mode=editing_mode,
            article_title=article_title,
            section_title=section_title,
            llm_config=llm_config,
        )

        # Build task parameters
        task_kwargs = cls.build_task_kwargs(
            edit_task_id=str(edit_task.id),
            article_title=article_title,
            section_title=section_title,
        )

        # Start processing task
        celery_task_id = cls.start_processing_task(
            editing_mode=editing_mode, llm_config=llm_config, task_kwargs=task_kwargs
        )

        # Update task with Celery ID
        cls.update_task_with_celery_id(edit_task, celery_task_id)

        # Return response data
        return {
            "task_id": str(edit_task.id),
            "status_url": f"/api/results/{edit_task.id}",
        }
