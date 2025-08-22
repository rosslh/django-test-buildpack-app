"""Tests for paragraph processor module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from services.core.constants import UNCHANGED_MARKER
from services.core.interfaces import (
    IReferenceHandler,
    IReversionTracker,
    ValidationContext,
)
from services.editing.paragraph_processor import ParagraphProcessor
from services.tracking.reversion_tracker import ReversionType
from services.validation.pipeline import (
    ValidationFailure,
    ValidationPipeline,
)


class MockReversionTracker(IReversionTracker):
    """Mock reversion tracker for testing."""

    def __init__(self):
        self.recorded_reversions = []

    def record_reversion(self, reversion_type: ReversionType) -> None:
        self.recorded_reversions.append(reversion_type)

    def get_summary(self) -> str:
        """Get summary of reversions."""
        return f"Total reversions: {len(self.recorded_reversions)}"

    def reset(self) -> None:
        """Reset the tracker."""
        self.recorded_reversions.clear()


class TestParagraphProcessor:
    """Test cases for ParagraphProcessor."""

    @pytest.fixture
    def mock_llm_chain(self):
        """Create a mock LLM chain."""
        chain = MagicMock(spec_set=["ainvoke"])
        chain.ainvoke = AsyncMock(return_value="Edited content")
        return chain

    @pytest.fixture
    def mock_pre_processing_pipeline(self):
        """Create a mock pre-processing pipeline."""
        pipeline = AsyncMock(spec=ValidationPipeline)
        pipeline.validate = AsyncMock(return_value=("content", False))
        return pipeline

    @pytest.fixture
    def mock_post_processing_pipeline(self):
        """Create a mock post-processing pipeline."""
        pipeline = AsyncMock(spec=ValidationPipeline)
        pipeline.validate = AsyncMock(return_value=("content", False))
        return pipeline

    @pytest.fixture
    def mock_reversion_tracker(self):
        """Create a mock reversion tracker."""
        return MockReversionTracker()

    @pytest.fixture
    def mock_reference_handler(self):
        """Fixture for a mock reference handler."""
        return AsyncMock(spec=IReferenceHandler)

    @pytest.fixture
    def processor(
        self,
        mock_llm_chain,
        mock_pre_processing_pipeline,
        mock_post_processing_pipeline,
        mock_reversion_tracker,
        mock_reference_handler,
    ):
        """Create a ParagraphProcessor instance with mocks."""
        return ParagraphProcessor(
            llm_chain=mock_llm_chain,
            pre_processing_pipeline=mock_pre_processing_pipeline,
            post_processing_pipeline=mock_post_processing_pipeline,
            reversion_tracker=mock_reversion_tracker,
            reference_handler=mock_reference_handler,
        )

    @pytest.fixture
    def validation_context(self):
        """Create a ValidationContext for testing."""
        return ValidationContext(
            paragraph_index=0,
            total_paragraphs=3,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

    def test_initialization(
        self,
        processor,
        mock_llm_chain,
        mock_pre_processing_pipeline,
        mock_post_processing_pipeline,
        mock_reversion_tracker,
    ):
        """Test ParagraphProcessor initialization."""
        assert processor.llm_chain is mock_llm_chain
        assert processor.pre_processing_pipeline is mock_pre_processing_pipeline
        assert processor.post_processing_pipeline is mock_post_processing_pipeline
        assert processor.reversion_tracker is mock_reversion_tracker
        assert processor.MAX_LLM_RETRIES == 3

    @pytest.mark.asyncio
    async def test_process_all_content_gets_processed(self, processor):
        """Test that all content gets processed since skipping now happens earlier in pipeline."""
        # Even short content should get processed since filtering happens earlier
        short_content = "Short"
        context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        # Mock the pipelines to allow the content to pass through
        processor.pre_processing_pipeline.validate = AsyncMock(
            return_value=(short_content, False)
        )
        processor.post_processing_pipeline.validate = AsyncMock(
            return_value=("Edited short content", False)
        )

        # Mock the LLM to return something
        with patch.object(
            processor, "_get_llm_edit", return_value="Edited short content"
        ):
            with patch(
                "services.text.output_cleaner.OutputCleaner.cleanup_llm_output",
                return_value="Edited short content",
            ):
                result = await processor.process(short_content, context)
                assert result.success
                assert result.content == "Edited short content"

    @pytest.mark.asyncio
    async def test_process_short_content_still_processes(
        self, processor, validation_context
    ):
        """Test process method with short content - no longer skipped at this level."""
        short_content = "Short"

        # Mock the pipelines to allow the content to pass through
        processor.pre_processing_pipeline.validate = AsyncMock(
            return_value=(short_content, False)
        )
        processor.post_processing_pipeline.validate = AsyncMock(
            return_value=(short_content, False)
        )

        # Mock LLM to return the content
        with patch.object(processor, "_get_llm_edit", return_value="Short"):
            with patch(
                "services.text.output_cleaner.OutputCleaner.cleanup_llm_output",
                return_value="Short",
            ):
                result = await processor.process(short_content, validation_context)

        assert result.success
        assert result.content == short_content

    @pytest.mark.asyncio
    async def test_process_successful_flow(
        self,
        processor,
        validation_context,
        mock_llm_chain,
        mock_pre_processing_pipeline,
        mock_post_processing_pipeline,
    ):
        """Test successful processing flow."""
        content = "This is a sufficiently long paragraph that should be processed successfully."
        edited_content = "This is an edited version of the paragraph."

        validation_context.additional_data = {"text_with_placeholders": content}

        # Mock pipeline responses
        mock_pre_processing_pipeline.validate.return_value = (content, False)
        mock_post_processing_pipeline.validate.return_value = (edited_content, False)
        mock_llm_chain.ainvoke.return_value = edited_content

        with patch("services.text.output_cleaner.OutputCleaner") as mock_cleaner:
            mock_cleaner.cleanup_llm_output.return_value = edited_content

            result = await processor.process(content, validation_context)

        assert result.success
        assert result.content == edited_content

        mock_pre_processing_pipeline.validate.assert_called_once()
        mock_post_processing_pipeline.validate.assert_called_once()
        mock_llm_chain.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_references(
        self,
        processor,
        validation_context,
        mock_llm_chain,
        mock_pre_processing_pipeline,
        mock_post_processing_pipeline,
        mock_reference_handler,
    ):
        """Test processing with reference restoration."""
        content = "This is a long enough content with references that should be processed properly."
        edited_content = "This is an edited version of the paragraph."
        final_content = "This is a long enough edited content with restored reference that should be processed properly."
        refs_list = ["<ref>test</ref>"]

        validation_context.additional_data = {
            "text_with_placeholders": content,
        }
        validation_context.refs_list = refs_list

        # Mock pipeline responses
        mock_pre_processing_pipeline.validate.return_value = (content, False)
        mock_post_processing_pipeline.validate.return_value = (edited_content, False)
        mock_llm_chain.ainvoke.return_value = edited_content
        mock_reference_handler.restore_references.return_value = final_content

        with patch("services.text.output_cleaner.OutputCleaner") as mock_cleaner:
            mock_cleaner.cleanup_llm_output.return_value = edited_content

            result = await processor.process(content, validation_context)

        assert result.success
        assert result.content == final_content
        mock_reference_handler.restore_references.assert_called_once_with(
            edited_content, refs_list
        )

    @pytest.mark.asyncio
    async def test_process_pre_processing_failure(
        self, processor, validation_context, mock_pre_processing_pipeline
    ):
        """Test pre-processing validation failure."""
        content = "This is some content."
        failure_reason = "Pre-processing failed"
        mock_pre_processing_pipeline.validate.return_value = (content, True)
        mock_pre_processing_pipeline.get_last_failure.return_value = ValidationFailure(
            "TestValidator", "pre", failure_reason, "orig", "edit"
        )

        result = await processor.process(content, validation_context)

        # Assertions
        assert not result.success
        assert result.content == content
        assert "Pre-processing validation failure" in result.failure_reason

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "failure_info, expected_reason",
        [
            (
                ValidationFailure(
                    "TestValidator", "sync", "Test reason", "content", "edited"
                ),
                "TestValidator: Test reason",
            ),
            (None, "Unknown post-processing failure"),
        ],
    )
    async def test_process_post_processing_failure(
        self,
        processor,
        validation_context,
        mock_llm_chain,
        mock_pre_processing_pipeline,
        mock_post_processing_pipeline,
        failure_info,
        expected_reason,
    ):
        """Test post-processing validation failure."""
        content = "This is some content."
        edited_content = "This is the edited content."

        # Mock pre-processing to succeed
        mock_pre_processing_pipeline.validate.return_value = (content, False)
        # Mock LLM chain to produce an edit
        mock_llm_chain.ainvoke.return_value = edited_content
        # Mock post-processing to fail
        mock_post_processing_pipeline.validate.return_value = (content, True)
        mock_post_processing_pipeline.get_last_failure.return_value = failure_info

        result = await processor.process(content, validation_context)

        # Assertions
        assert not result.success
        assert result.content == content
        assert "Post-processing validation failure" in result.failure_reason
        assert expected_reason in result.failure_reason

    @pytest.mark.asyncio
    async def test_process_llm_returns_none(
        self,
        processor,
        validation_context,
        mock_llm_chain,
        mock_pre_processing_pipeline,
    ):
        """Test processing when LLM returns None."""
        content = "Content where LLM fails"

        validation_context.additional_data = {"text_with_placeholders": content}
        mock_pre_processing_pipeline.validate.return_value = (content, False)

        with patch.object(processor, "_get_llm_edit", return_value=None):
            result = await processor.process(content, validation_context)

        assert not result.success
        assert result.content == content
        assert result.failure_reason == "LLM did not return any content"

    @pytest.mark.asyncio
    async def test_process_llm_returns_empty(
        self,
        processor,
        validation_context,
        mock_llm_chain,
        mock_pre_processing_pipeline,
    ):
        """Test processing when LLM returns empty content."""
        content = "Content where LLM returns empty"

        validation_context.additional_data = {"text_with_placeholders": content}
        mock_pre_processing_pipeline.validate.return_value = (content, False)
        mock_llm_chain.ainvoke.return_value = ""

        with patch("services.text.output_cleaner.OutputCleaner") as mock_cleaner:
            mock_cleaner.cleanup_llm_output.return_value = ""

            result = await processor.process(content, validation_context)

        assert not result.success
        assert result.content == content
        assert result.failure_reason == "LLM did not return any content"

    @pytest.mark.asyncio
    async def test_process_llm_returns_unchanged_marker(
        self,
        processor,
        validation_context,
        mock_llm_chain,
        mock_pre_processing_pipeline,
        mock_post_processing_pipeline,
    ):
        """Test process when LLM returns the UNCHANGED_MARKER."""
        content = "This is a long enough content that LLM decides not to change and should be processed properly."
        validation_context.additional_data = {"text_with_placeholders": content}

        mock_pre_processing_pipeline.validate.return_value = (content, False)
        mock_llm_chain.ainvoke.return_value = UNCHANGED_MARKER

        with patch(
            "services.text.output_cleaner.OutputCleaner.cleanup_llm_output",
            return_value=UNCHANGED_MARKER,
        ):
            result = await processor.process(content, validation_context)

        assert result.success
        assert result.content == content

        assert result.content == content
        mock_post_processing_pipeline.validate.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_llm_edit_success(self, mock_reference_handler):
        """Test successful LLM edit retrieval."""
        llm_chain = AsyncMock()
        llm_chain.ainvoke.return_value = "Edited text from LLM"

        processor = ParagraphProcessor(
            llm_chain,
            AsyncMock(),
            AsyncMock(),
            MockReversionTracker(),
            mock_reference_handler,
        )

        context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        result = await processor._get_llm_edit("test text", context)
        assert result == "Edited text from LLM"

    @pytest.mark.asyncio
    async def test_process_api_exception(
        self, processor, validation_context, mock_reversion_tracker
    ):
        pass

    def test_handle_processing_error_api_error(
        self, processor, validation_context, mock_reversion_tracker
    ):
        """Test handling of API errors."""
        error = ChatGoogleGenerativeAIError("API error")
        processor._handle_processing_error(error, "content", validation_context)
        assert mock_reversion_tracker.recorded_reversions == [ReversionType.API_ERROR]

    def test_handle_processing_error_unexpected_error(
        self, processor, validation_context, mock_reversion_tracker
    ):
        """Test handling of unexpected errors."""
        error = Exception("Unexpected error")
        processor._handle_processing_error("content", error, validation_context)
        assert mock_reversion_tracker.recorded_reversions == [
            ReversionType.UNEXPECTED_ERROR
        ]

    @pytest.mark.asyncio
    async def test_process_no_text_with_placeholders(
        self, processor, validation_context, mock_pre_processing_pipeline
    ):
        """Test process when additional_data doesn't contain text_with_placeholders."""
        # Don't set text_with_placeholders in additional_data
        validation_context.additional_data = {}
        mock_pre_processing_pipeline.validate.return_value = (None, False)
        result = await processor.process("content", validation_context)
        assert result.success
        assert result.content == "content"

    @pytest.mark.asyncio
    async def test_get_llm_edit_non_api_exception_propagation(
        self, mock_reference_handler
    ):
        # Create mock components
        mock_llm_chain = AsyncMock()
        mock_pre_processing_pipeline = MagicMock()
        mock_post_processing_pipeline = MagicMock()
        mock_reversion_tracker = MagicMock()

        processor = ParagraphProcessor(
            llm_chain=mock_llm_chain,
            pre_processing_pipeline=mock_pre_processing_pipeline,
            post_processing_pipeline=mock_post_processing_pipeline,
            reversion_tracker=mock_reversion_tracker,
            reference_handler=mock_reference_handler,
        )

        # Create validation context
        validation_context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        # Test the final fall-through case in _get_llm_edit
        # Make the LLM chain fail with a non-API error that doesn't trigger the except block
        mock_llm_chain.ainvoke.side_effect = [
            Exception("Non-API error that shouldn't be caught"),
        ]

        # This should propagate the non-API exception
        with pytest.raises(Exception, match="Non-API error"):
            await processor._get_llm_edit("test text", validation_context)

    @pytest.mark.asyncio
    async def test_prompt_template_contains_correct_markup(
        self, mock_reference_handler
    ):
        """Test that the prompt template contains correct {{...}} markup when rendered."""
        from services.prompts.prompt_manager import PromptManager

        # Create a mock LLM chain that captures the rendered prompt
        captured_prompt = None

        class PromptCapturingChain:
            def __init__(self, prompt_template):
                self.prompt_template = prompt_template

            async def ainvoke(self, variables):
                nonlocal captured_prompt
                # Render the template with the provided variables
                captured_prompt = self.prompt_template.format(**variables)
                return "Mock LLM response"

        # Create real prompt manager and get a template
        prompt_manager = PromptManager()
        template = prompt_manager.get_template("copyedit")

        # Create the chain with the real template
        chain = PromptCapturingChain(template)

        # Create processor with the capturing chain
        processor = ParagraphProcessor(
            llm_chain=chain,
            pre_processing_pipeline=AsyncMock(),
            post_processing_pipeline=AsyncMock(),
            reversion_tracker=MagicMock(),
            reference_handler=mock_reference_handler,
        )

        # Create validation context
        validation_context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        # Call _get_llm_edit which will render the template
        await processor._get_llm_edit("Test wikitext content", validation_context)

        # Verify the rendered prompt contains the correct markup
        assert captured_prompt is not None, "Prompt should have been captured"
        assert "{{...}}" in captured_prompt, (
            "Prompt should contain {{...}} markup for templates"
        )
        assert "{{sfn}}" in captured_prompt, "Prompt should contain {{sfn}} example"
        assert "{{ref}}" in captured_prompt, "Prompt should contain {{ref}} example"

    @pytest.mark.asyncio
    async def test_get_llm_edit_last_attempt_failure_records_reversion(
        self, mock_reference_handler
    ):
        """Test that the last attempt failure records a reversion and returns None."""
        mock_reversion_tracker = MockReversionTracker()
        mock_llm_chain = MagicMock()

        # Make all attempts fail with an API error
        mock_llm_chain.ainvoke = AsyncMock(
            side_effect=ChatGoogleGenerativeAIError("API error")
        )

        processor = ParagraphProcessor(
            llm_chain=mock_llm_chain,
            pre_processing_pipeline=AsyncMock(),
            post_processing_pipeline=AsyncMock(),
            reversion_tracker=mock_reversion_tracker,
            reference_handler=mock_reference_handler,
        )

        context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        # Mock asyncio.sleep to avoid actual delays
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await processor._get_llm_edit("test text", context)

            # Should return None
            assert result is None

            # Should record a reversion on the last attempt
            assert len(mock_reversion_tracker.recorded_reversions) == 1
            assert (
                mock_reversion_tracker.recorded_reversions[0] == ReversionType.API_ERROR
            )

            # Verify all attempts were made
            assert mock_llm_chain.ainvoke.call_count == processor.MAX_LLM_RETRIES

    @pytest.mark.asyncio
    async def test_process_general_exception_handling(self):
        """Test that general exceptions during processing are handled gracefully."""
        # Setup mocks to simulate a general exception during pre-processing
        mock_pre_processing_pipeline = AsyncMock()
        mock_pre_processing_pipeline.validate.side_effect = Exception(
            "Unexpected error"
        )
        mock_reversion_tracker = MockReversionTracker()

        processor = ParagraphProcessor(
            llm_chain=AsyncMock(),
            pre_processing_pipeline=mock_pre_processing_pipeline,
            post_processing_pipeline=AsyncMock(),
            reversion_tracker=mock_reversion_tracker,
            reference_handler=AsyncMock(),
        )

        context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        # Should handle the exception and return original content
        result = await processor.process("original content", context)

        assert not result.success
        assert result.failure_reason is not None
        assert "Unexpected error" in result.failure_reason
        assert result.content == "original content"
        assert mock_reversion_tracker.recorded_reversions == [
            ReversionType.UNEXPECTED_ERROR
        ]

    @pytest.mark.asyncio
    async def test_apollo_link_validation_failure_integration(self):
        """
        Integration test reproducing the Apollo validation failure.

        This test reproduces the specific scenario where:
        1. Original text has no Apollo link
        2. LLM adds an Apollo link
        3. WikiLinkValidator should remove it during post-processing
        4. But AddedContentValidatorAdapter still detects it and causes failure

        This tests the actual pipeline integration to identify the root cause.
        """
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.pipeline import ValidationPipelineBuilder
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        # Create real components
        reference_handler = ReferenceHandler()
        reference_validator = ReferenceValidator()
        wiki_link_validator = WikiLinkValidator(reference_handler)

        # Create real validation pipeline similar to edit_service.py
        builder = ValidationPipelineBuilder()

        # Add WikiLinkValidatorAdapter first (should remove Apollo link)
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        # Add AddedContentValidatorAdapter later (should not detect Apollo link)
        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        post_processing_pipeline = builder.build()

        # Mock LLM to add Apollo link
        mock_llm_chain = AsyncMock()
        mock_llm_chain.ainvoke.return_value = (
            "The [[Apollo]] mission was successful and achieved its objectives."
        )

        # Create processor with real post-processing pipeline
        processor = ParagraphProcessor(
            llm_chain=mock_llm_chain,
            pre_processing_pipeline=AsyncMock(),  # Mock pre-processing
            post_processing_pipeline=post_processing_pipeline,  # Real post-processing
            reversion_tracker=MockReversionTracker(),
            reference_handler=reference_handler,
        )

        # Setup for processing
        original_content = "The mission was successful and achieved its objectives."
        context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={"text_with_placeholders": original_content},
        )

        # Mock pre-processing to pass through
        with patch.object(
            processor.pre_processing_pipeline,
            "validate",
            return_value=(original_content, False),
        ):
            # Mock OutputCleaner to return LLM output as-is
            with patch(
                "services.text.output_cleaner.OutputCleaner.cleanup_llm_output"
            ) as mock_cleaner:
                mock_cleaner.return_value = (
                    "The [[Apollo]] mission was successful and achieved its objectives."
                )

                # Process the content
                result = await processor.process(original_content, context)

        # The result should be the cleaned content, not reverted.
        # The WikiLinkValidator should have removed the [[Apollo]] link.
        assert "[[Apollo]]" not in result.content
        assert (
            result.content
            == "The Apollo mission was successful and achieved its objectives."
        ), (
            "The content should be cleaned, with the Apollo link markup removed but the text preserved."
        )

        # Check that no failure reason was set
        assert result.success is True and result.failure_reason is None, (
            "Should not have a failure reason, because the edit should succeed."
        )

    @pytest.mark.asyncio
    async def test_apollo_link_pipeline_order_debug(self):
        """
        Debug test to verify the order of validation and what each validator sees.

        This test helps debug the exact state of content at each stage of validation.
        """

        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.pipeline import ValidationPipelineBuilder
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        reference_handler = ReferenceHandler()
        reference_validator = ReferenceValidator()
        wiki_link_validator = WikiLinkValidator(reference_handler)

        # Create pipeline
        builder = ValidationPipelineBuilder()

        # Add validators in same order as edit_service.py
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        post_processing_pipeline = builder.build()

        # Simulate the exact scenario
        original_content = "The mission was successful and achieved its objectives."
        llm_added_apollo = (
            "The [[Apollo]] mission was successful and achieved its objectives."
        )

        # Run post-processing validation directly
        final_text, should_revert = await post_processing_pipeline.validate(
            original_content,  # original
            llm_added_apollo,  # edited (with Apollo link added)
            {
                "paragraph_index": 0,
                "total_paragraphs": 1,
                "refs_list": [],
            },
        )

        # Print debug info for analysis
        print("======================")
        print(f"Original: {original_content}")
        print(f"LLM Output: {llm_added_apollo}")
        print(f"Final Text: {final_text}")
        print(f"Should Revert: {should_revert}")

        # If working correctly:
        # 1. WikiLinkValidator should remove [[Apollo]] link
        # 2. AddedContentValidatorAdapter should see no new links
        # 3. should_revert should be False
        # 4. final_text should be "The Apollo mission was successful and achieved its objectives."

        if should_revert:
            # If this happens, it means the pipeline has the bug
            failure_info = post_processing_pipeline.get_last_failure()
            failure_reason = failure_info.reason if failure_info else "Unknown"
            print(f"PIPELINE FAILURE: {failure_reason}")

            # This indicates the bug exists
            raise AssertionError(
                f"Pipeline should not revert when WikiLinkValidator removes new links. "
                f"Failure reason: {failure_reason}"
            )
        else:
            # Pipeline worked correctly
            assert "[[Apollo]]" not in final_text, (
                "Apollo link should be removed by WikiLinkValidator"
            )
            assert "Apollo" in final_text, (
                "Apollo text should remain (just link markup removed)"
            )

    @pytest.mark.asyncio
    async def test_get_llm_edit_no_retries_configured(self, processor):
        """Test _get_llm_edit when MAX_LLM_RETRIES is set to 0."""
        context = ValidationContext(
            paragraph_index=0,
            total_paragraphs=1,
            is_first_prose=False,
            refs_list=[],
            additional_data={},
        )

        original_max_retries = processor.MAX_LLM_RETRIES
        processor.MAX_LLM_RETRIES = 0

        try:
            result = await processor._get_llm_edit("test text", context)
            # Should return None due to no retries configured
            assert result is None
        finally:
            # Restore original value
            processor.MAX_LLM_RETRIES = original_max_retries
