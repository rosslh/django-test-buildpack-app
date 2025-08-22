"""Paragraph processor for handling individual paragraph editing.

This module is responsible for processing individual paragraphs through the editing
pipeline, separating this concern from orchestration.
"""

import asyncio
from typing import Any, Optional

import httpx
from google.api_core.exceptions import GoogleAPIError
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from services.core.constants import UNCHANGED_MARKER
from services.core.interfaces import (
    IParagraphProcessor,
    IReferenceHandler,
    IReversionTracker,
    ParagraphProcessingResult,
    ValidationContext,
)
from services.text.output_cleaner import OutputCleaner
from services.tracking.reversion_tracker import ReversionType
from services.validation.pipeline import ValidationPipeline


class ParagraphProcessor(IParagraphProcessor):
    """Processes individual paragraphs through the editing pipeline.

    This class is responsible for the actual editing logic of individual paragraphs,
    including LLM interaction and validation.
    """

    # Constants
    MAX_LLM_RETRIES = 3

    def __init__(
        self,
        llm_chain: Any,
        pre_processing_pipeline: ValidationPipeline,
        post_processing_pipeline: ValidationPipeline,
        reversion_tracker: IReversionTracker,
        reference_handler: IReferenceHandler,
    ):
        self.llm_chain = llm_chain
        self.pre_processing_pipeline = pre_processing_pipeline
        self.post_processing_pipeline = post_processing_pipeline
        self.reversion_tracker = reversion_tracker
        self.reference_handler = reference_handler

    async def process(
        self, content: str, context: ValidationContext
    ) -> ParagraphProcessingResult:
        """Process a single paragraph through the editing pipeline.

        Args:
            content: The paragraph content to process
            context: Validation context with metadata

        Returns:
            The processed paragraph content
        """
        intermediate_steps = {}

        try:
            # Get text with placeholders from context
            text_with_placeholders = context.additional_data.get(
                "text_with_placeholders", content
            )
            intermediate_steps["Text with Placeholders"] = text_with_placeholders

            # Run pre-processing validations
            (
                validated_text,
                should_revert,
            ) = await self.pre_processing_pipeline.validate(
                content, text_with_placeholders, context.__dict__
            )

            if should_revert:
                failure_info = self.pre_processing_pipeline.get_last_failure()
                failure_reason = (
                    failure_info.reason
                    if failure_info
                    else "Unknown pre-processing failure"
                )
                return ParagraphProcessingResult(
                    success=False,
                    content=content,
                    failure_reason=f"Pre-processing validation failure: {failure_reason}",
                )

            # Get LLM edit
            raw_llm_output = await self._get_llm_edit(validated_text, context)
            intermediate_steps["Raw LLM Output"] = raw_llm_output

            if not raw_llm_output:
                return ParagraphProcessingResult(
                    success=False,
                    content=content,
                    failure_reason="LLM did not return any content",
                )

            # Clean LLM output
            cleaned_llm_output = OutputCleaner.cleanup_llm_output(raw_llm_output)
            intermediate_steps["Cleaned LLM Output"] = cleaned_llm_output

            # Check for unchanged marker
            if not cleaned_llm_output or cleaned_llm_output.strip() == UNCHANGED_MARKER:
                return ParagraphProcessingResult(success=True, content=content)

            # Run post-processing validations
            final_text, should_revert = await self.post_processing_pipeline.validate(
                content, cleaned_llm_output, context.__dict__
            )

            if should_revert:
                failure_info = self.post_processing_pipeline.get_last_failure()
                if failure_info:
                    failure_reason = (
                        f"{failure_info.validator_name}: {failure_info.reason}"
                    )
                else:
                    failure_reason = "Unknown post-processing failure"

                return ParagraphProcessingResult(
                    success=False,
                    content=content,
                    failure_reason=f"Post-processing validation failure: {failure_reason}",
                )

            # Restore references if needed
            if context.refs_list:
                final_text = self.reference_handler.restore_references(
                    final_text, context.refs_list
                )

            return ParagraphProcessingResult(success=True, content=final_text)

        except Exception as e:
            self._handle_processing_error(e, content, context)
            return ParagraphProcessingResult(
                success=False,
                content=content,
                failure_reason=f"Processing error: {str(e)}",
            )

    async def _get_llm_edit(
        self, text: str, context: ValidationContext
    ) -> Optional[str]:
        """Get edited text from the language model with retries."""
        for attempt in range(self.MAX_LLM_RETRIES):
            try:
                # Use the variable names expected by the prompt template
                result = await self.llm_chain.ainvoke(
                    {
                        "wikitext": text,  # Changed from "text" to "wikitext"
                    }
                )
                return result

            except (
                ChatGoogleGenerativeAIError,
                GoogleAPIError,
                httpx.ReadTimeout,
            ):
                if attempt >= self.MAX_LLM_RETRIES - 1:
                    self.reversion_tracker.record_reversion(ReversionType.API_ERROR)
                    return None
                await asyncio.sleep(2**attempt)
        return None

    def _handle_processing_error(
        self, error: Exception, original: str, context: ValidationContext
    ) -> None:
        """Handle errors during paragraph processing."""
        # Record appropriate reversion type
        if isinstance(
            error, (ChatGoogleGenerativeAIError, GoogleAPIError, httpx.ReadTimeout)
        ):
            self.reversion_tracker.record_reversion(ReversionType.API_ERROR)
        else:
            self.reversion_tracker.record_reversion(ReversionType.UNEXPECTED_ERROR)
