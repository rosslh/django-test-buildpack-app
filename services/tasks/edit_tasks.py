import asyncio
from dataclasses import asdict

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from langchain_anthropic.chat_models import ChatAnthropic
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_openai.chat_models import ChatOpenAI
from langchain_perplexity.chat_models import ChatPerplexity

from api.exceptions import ErrorSanitizer, ValidationError
from data.models.edit_task import EditTask
from services.core.constants import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_MISTRAL_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_PARAGRAPH_BATCH_SIZE,
    DEFAULT_PERPLEXITY_MODEL,
)
from services.editing.edit_service import WikiEditor
from services.security.encryption_service import EncryptionService
from services.utils.wikipedia_api import WikipediaAPI


@shared_task(bind=True)
def process_edit_task_batched(
    self,
    editing_mode,
    encrypted_llm_config,
    edit_task_id,
    batch_size=DEFAULT_PARAGRAPH_BATCH_SIZE,
    **kwargs,
):
    """Process an editing task with batched paragraph processing to reduce task overhead.

    Args:
        self: The task instance (provided by Celery)
        editing_mode: The editing mode to apply ('brevity' or 'copyedit')
        encrypted_llm_config: Encrypted configuration for initializing the LLM
        edit_task_id: UUID of the EditTask record to update
        batch_size: Number of paragraphs to process per batch (default from constants)
        **kwargs: Additional arguments including:
            - article_title and section_title for section editing

    Returns:
        dict: The results of the editing operation (stored in EditTask model)
    """
    # Get the EditTask from database
    try:
        edit_task = EditTask.objects.get(id=edit_task_id)
    except ObjectDoesNotExist:
        return {"error": f"EditTask with id {edit_task_id} not found"}

    try:
        # Mark task as started
        edit_task.mark_started()

        # Decrypt the LLM configuration
        encryption_service = EncryptionService()
        llm_config = encryption_service.decrypt_dict(encrypted_llm_config)

        # Initialize the LLM based on the provided configuration
        llm = _initialize_llm(llm_config)

        # Update model information in the EditTask
        provider = llm_config.get("provider", "")
        model_name = {
            "google": DEFAULT_GEMINI_MODEL,
            "openai": DEFAULT_OPENAI_MODEL,
            "anthropic": DEFAULT_ANTHROPIC_MODEL,
            "mistral": DEFAULT_MISTRAL_MODEL,
            "perplexity": DEFAULT_PERPLEXITY_MODEL,
        }.get(provider, DEFAULT_OPENAI_MODEL)
        edit_task.llm_model = model_name
        edit_task.save(update_fields=["llm_model"])

        # Initialize the WikiEditor with batching enabled
        editor = WikiEditor(llm=llm, editing_mode=editing_mode, verbose=False)

        # Create enhanced progress callback
        def enhanced_progress_callback(progress_data):
            """Enhanced progress callback that updates with granular phase information."""
            edit_task.update_progress_enhanced(progress_data)  # pragma: no cover

        # Process article section with batching
        article_title = kwargs.get("article_title")
        section_title = kwargs.get("section_title")

        # Ensure types are str for mypy
        if not isinstance(article_title, str) or not isinstance(section_title, str):
            raise ValidationError(
                "article_title and section_title must be provided as strings"
            )

        paragraph_results = _run_async_safely(
            editor.edit_article_section_structured_batched(
                article_title,
                section_title,
                "en",
                enhanced_progress_callback,
                batch_size,
            )
        )

        # Get article URL
        wikipedia_api = WikipediaAPI()
        article_url = wikipedia_api.get_article_url(article_title)

        # Filter out any results with empty before/after fields
        valid_results = _filter_valid_results(paragraph_results)

        response_data = {
            "paragraphs": [asdict(p) for p in valid_results],
        }
        if article_title:
            response_data["article_title"] = str(article_title)  # type: ignore
        if section_title:
            response_data["section_title"] = str(section_title)  # type: ignore
        if article_url:
            response_data["article_url"] = str(article_url)  # type: ignore

        # Mark task as successful and store results
        edit_task.mark_success(response_data)
        return response_data

    except Exception as e:
        # Sanitize the error message before storing
        sanitized_error = ErrorSanitizer.sanitize_exception(e)
        error_message = sanitized_error.user_message

        # Mark task as failed and store sanitized error
        edit_task.mark_failure(error_message)
        return {"error": error_message}


@shared_task(bind=True)
def process_edit_task(self, editing_mode, encrypted_llm_config, edit_task_id, **kwargs):
    """Process an editing task asynchronously.

    Args:
        self: The task instance (provided by Celery)
        editing_mode: The editing mode to apply ('brevity' or 'copyedit')
        encrypted_llm_config: Encrypted configuration for initializing the LLM
        edit_task_id: UUID of the EditTask record to update
        **kwargs: Additional arguments including:
            - article_title and section_title for section editing

    Returns:
        dict: The results of the editing operation (stored in EditTask model)
    """
    # Get the EditTask from database
    try:
        edit_task = EditTask.objects.get(id=edit_task_id)
    except ObjectDoesNotExist:
        return {"error": f"EditTask with id {edit_task_id} not found"}

    try:
        # Mark task as started
        edit_task.mark_started()

        # Decrypt the LLM configuration
        encryption_service = EncryptionService()
        llm_config = encryption_service.decrypt_dict(encrypted_llm_config)

        # Initialize the LLM based on the provided configuration
        llm = _initialize_llm(llm_config)

        # Update model information in the EditTask
        provider = llm_config.get("provider", "")
        model_name = {
            "google": DEFAULT_GEMINI_MODEL,
            "openai": DEFAULT_OPENAI_MODEL,
            "anthropic": DEFAULT_ANTHROPIC_MODEL,
            "mistral": DEFAULT_MISTRAL_MODEL,
            "perplexity": DEFAULT_PERPLEXITY_MODEL,
        }.get(provider, DEFAULT_OPENAI_MODEL)
        edit_task.llm_model = model_name
        edit_task.save(update_fields=["llm_model"])

        # Initialize the WikiEditor
        editor = WikiEditor(llm=llm, editing_mode=editing_mode, verbose=False)

        # Create enhanced progress callback
        def enhanced_progress_callback(progress_data):
            """Enhanced progress callback that updates with granular phase information."""
            edit_task.update_progress_enhanced(progress_data)  # pragma: no cover

        # Process article section
        article_title = kwargs.get("article_title")
        section_title = kwargs.get("section_title")

        # Ensure types are str for mypy
        if not isinstance(article_title, str) or not isinstance(section_title, str):
            raise ValidationError(
                "article_title and section_title must be provided as strings"
            )

        paragraph_results = _run_async_safely(
            editor.edit_article_section_structured(
                article_title, section_title, "en", enhanced_progress_callback
            )
        )

        # Get article URL
        wikipedia_api = WikipediaAPI()
        article_url = wikipedia_api.get_article_url(article_title)

        # Filter out any results with empty before/after fields
        valid_results = _filter_valid_results(paragraph_results)

        response_data = {
            "paragraphs": [asdict(p) for p in valid_results],
        }
        if article_title:
            response_data["article_title"] = str(article_title)  # type: ignore
        if section_title:
            response_data["section_title"] = str(section_title)  # type: ignore
        if article_url:
            response_data["article_url"] = str(article_url)  # type: ignore

        # Mark task as successful and store results
        edit_task.mark_success(response_data)
        return response_data

    except Exception as e:
        # Sanitize the error message before storing
        sanitized_error = ErrorSanitizer.sanitize_exception(e)
        error_message = sanitized_error.user_message

        # Mark task as failed and store sanitized error
        edit_task.mark_failure(error_message)
        return {"error": error_message}


def _run_async_safely(coro):
    """Safely run an async coroutine in a potentially async context.

    This function handles event loop conflicts that can occur when running
    async code in Celery tasks or other environments where an event loop
    might already be running.
    """
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()
        # If we're already in an event loop, we can't use asyncio.run()
        # Instead, we need to use a different approach
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No event loop is running, safe to use asyncio.run()
        return asyncio.run(coro)


def _initialize_llm(llm_config):
    """Initialize the appropriate LLM based on configuration."""
    provider = llm_config.get("provider")
    api_key = llm_config.get("api_key")

    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=DEFAULT_GEMINI_MODEL, temperature=0, google_api_key=api_key
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=DEFAULT_OPENAI_MODEL,
            temperature=0,
            api_key=api_key,
        )
    elif provider == "anthropic":
        return ChatAnthropic(
            model_name=DEFAULT_ANTHROPIC_MODEL,
            temperature=0,
            api_key=api_key,
            timeout=None,
            stop=None,
        )
    elif provider == "mistral":
        return ChatMistralAI(
            temperature=0,
            api_key=api_key,
        )
    elif provider == "perplexity":
        return ChatPerplexity(
            model=DEFAULT_PERPLEXITY_MODEL,
            temperature=0,
            api_key=api_key,
            timeout=None,
        )
    else:
        raise ValidationError(f"Invalid LLM provider specified: {provider}")


def _filter_valid_results(paragraph_results):
    """Filter out results with empty before/after fields."""
    valid_results = []
    for result in paragraph_results:
        if result.before.strip() and result.after.strip():
            valid_results.append(result)

    return valid_results
