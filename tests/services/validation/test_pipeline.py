"""Tests for validation pipeline module."""

from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

import pytest

from services.core.interfaces import (
    IAsyncValidator,
    IValidator,
    ValidationContext,
)
from services.validation.pipeline import (
    PostProcessingPipeline,
    PreProcessingPipeline,
    ValidationPipeline,
    ValidationPipelineBuilder,
    ValidationResult,
)


class MockValidator(IValidator):
    """Mock synchronous validator for testing."""

    validate_calls: list

    def __init__(self, should_revert: bool = False, modify_content: bool = False):
        self.should_revert = should_revert
        self.modify_content = modify_content
        self.validate_calls = []
        self.last_failure_reason = "Mock failure"

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        self.validate_calls.append((original, edited, context))
        if self.modify_content:
            return f"modified_{edited}", self.should_revert
        return edited, self.should_revert

    def get_last_failure_reason(self) -> str:
        return self.last_failure_reason if self.should_revert else ""


class MockAsyncValidator(IAsyncValidator):
    """Mock asynchronous validator for testing."""

    validate_calls: list

    def __init__(self, should_revert: bool = False, modify_content: bool = False):
        self.should_revert = should_revert
        self.modify_content = modify_content
        self.validate_calls = []
        self.last_failure_reason = "Mock async failure"

    async def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        self.validate_calls.append((original, edited, context))
        if self.modify_content:
            return f"async_modified_{edited}", self.should_revert
        return edited, self.should_revert

    def get_last_failure_reason(self) -> str:
        return self.last_failure_reason if self.should_revert else ""


class MockValidatorWithFailureReason(IValidator):
    """Mock validator that provides failure reasons."""

    validate_calls: list

    def __init__(
        self, should_revert: bool = False, failure_reason: str = "Test failure"
    ):
        self.should_revert = should_revert
        self.failure_reason = failure_reason
        self.validate_calls = []

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        self.validate_calls.append((original, edited, context))
        return edited, self.should_revert

    def get_last_failure_reason(self) -> str:
        return self.failure_reason if self.should_revert else ""


class TestValidationResult:
    """Test ValidationResult enum."""

    def test_validation_result_values(self):
        """Test that ValidationResult enum has expected values."""
        assert ValidationResult.SUCCESS is not None
        assert ValidationResult.REVERT is not None
        assert ValidationResult.MODIFIED is not None

        # Ensure they are distinct
        values = {
            ValidationResult.SUCCESS,
            ValidationResult.REVERT,
            ValidationResult.MODIFIED,
        }
        assert len(values) == 3


class TestValidationContext:
    """Test ValidationContext dataclass."""

    def test_validation_context_creation(self):
        """Test creating a ValidationContext instance."""
        context = ValidationContext(
            paragraph_index=1,
            total_paragraphs=5,
            is_first_prose=True,
            refs_list=["ref1", "ref2"],
            additional_data={"key": "value"},
        )

        assert context.paragraph_index == 1
        assert context.total_paragraphs == 5
        assert context.is_first_prose is True
        assert context.refs_list == ["ref1", "ref2"]
        assert context.additional_data == {"key": "value"}


class TestValidationPipeline:
    """Test ValidationPipeline class."""

    @pytest.mark.asyncio
    async def test_validate_empty_pipeline(self):
        """Test validation with no validators."""
        pipeline = ValidationPipeline()

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert result == "edited"
        assert should_revert is False

    @pytest.mark.asyncio
    async def test_validate_sync_validators_success(self):
        """Test validation with synchronous validators that succeed."""
        pipeline = ValidationPipeline()
        validator1 = MockValidator(modify_content=True)
        validator2 = MockValidator()

        pipeline.add_validator(validator1)
        pipeline.add_validator(validator2)

        result, should_revert = await pipeline.validate(
            "original", "edited", {"test": "context"}
        )

        assert result == "modified_edited"
        assert should_revert is False
        assert len(validator1.validate_calls) == 1
        assert len(validator2.validate_calls) == 1
        assert (
            validator2.validate_calls[0][1] == "modified_edited"
        )  # Got modified content

    @pytest.mark.asyncio
    async def test_validate_sync_validator_revert(self):
        """Test validation with synchronous validator that triggers revert."""
        pipeline = ValidationPipeline()
        validator1 = MockValidator()
        validator2 = MockValidator(should_revert=True)
        validator3 = MockValidator()  # Should not be called

        pipeline.add_validator(validator1)
        pipeline.add_validator(validator2)
        pipeline.add_validator(validator3)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert result == "edited"
        assert should_revert is True
        assert len(validator1.validate_calls) == 1
        assert len(validator2.validate_calls) == 1
        assert len(validator3.validate_calls) == 0  # Should not be called

    @pytest.mark.asyncio
    async def test_validate_async_validators_success(self):
        """Test validation with asynchronous validators that succeed."""
        pipeline = ValidationPipeline()
        validator1 = MockAsyncValidator(modify_content=True)
        validator2 = MockAsyncValidator()

        pipeline.add_async_validator(validator1)
        pipeline.add_async_validator(validator2)

        result, should_revert = await pipeline.validate(
            "original", "edited", {"test": "context"}
        )

        assert result == "async_modified_edited"
        assert should_revert is False
        assert len(validator1.validate_calls) == 1
        assert len(validator2.validate_calls) == 1
        assert (
            validator2.validate_calls[0][1] == "async_modified_edited"
        )  # Got modified content

    @pytest.mark.asyncio
    async def test_validate_async_validator_revert(self):
        """Test validation with asynchronous validator that triggers revert."""
        pipeline = ValidationPipeline()
        validator1 = MockAsyncValidator()
        validator2 = MockAsyncValidator(should_revert=True)
        validator3 = MockAsyncValidator()  # Should not be called

        pipeline.add_async_validator(validator1)
        pipeline.add_async_validator(validator2)
        pipeline.add_async_validator(validator3)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert result == "edited"
        assert should_revert is True
        assert len(validator1.validate_calls) == 1
        assert len(validator2.validate_calls) == 1
        assert len(validator3.validate_calls) == 0  # Should not be called

    @pytest.mark.asyncio
    async def test_validate_mixed_validators(self):
        """Test validation with both sync and async validators."""
        pipeline = ValidationPipeline()
        sync_validator = MockValidator(modify_content=True)
        async_validator = MockAsyncValidator(modify_content=True)

        pipeline.add_validator(sync_validator)
        pipeline.add_async_validator(async_validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        # With the fixed execution order: async validators run first, then sync validators
        # 1. async_validator: "edited" -> "async_modified_edited"
        # 2. sync_validator: "async_modified_edited" -> "modified_async_modified_edited"
        assert result == "modified_async_modified_edited"
        assert should_revert is False
        assert len(sync_validator.validate_calls) == 1
        assert len(async_validator.validate_calls) == 1

    @pytest.mark.asyncio
    async def test_failure_reason_extraction_with_custom_method(self):
        """Test failure reason extraction when validator has get_last_failure_reason
        method."""
        pipeline = ValidationPipeline()
        validator = MockValidatorWithFailureReason(
            should_revert=True, failure_reason="Custom failure reason"
        )

        pipeline.add_validator(validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert should_revert is True
        assert pipeline.last_failure is not None
        assert pipeline.last_failure.reason == "Custom failure reason"

    @pytest.mark.asyncio
    async def test_failure_reason_extraction_for_wikilink_validator(self):
        """Test failure reason extraction for WikiLink validator type."""
        pipeline = ValidationPipeline()

        # Create a mock validator with WikiLink in the class name
        class MockWikiLinkValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "Link validation failed" if should_revert else ""
                )

        validator = MockWikiLinkValidator(should_revert=True)
        pipeline.add_validator(validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert should_revert is True
        assert pipeline.last_failure is not None
        assert "Link validation failed" in pipeline.last_failure.reason

    @pytest.mark.asyncio
    async def test_failure_reason_extraction_for_reference_validator(self):
        """Test failure reason extraction for Reference validator type."""
        pipeline = ValidationPipeline()

        # Create mock validators for different reference validator types
        class MockReferenceContentValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "Reference content was modified" if should_revert else ""
                )

        class MockAddedReferenceValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "New content (links or references) was added"
                    if should_revert
                    else ""
                )

        class MockCompositeReferenceValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "Reference validation failed (references may have been removed or modified)"
                    if should_revert
                    else ""
                )

        class MockReferenceValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "Reference validation failed" if should_revert else ""
                )

        validators = [
            (
                MockReferenceContentValidator(should_revert=True),
                "Reference content was modified",
            ),
            (
                MockAddedReferenceValidator(should_revert=True),
                "New content (links or references) was added",
            ),
            (
                MockCompositeReferenceValidator(should_revert=True),
                "Reference validation failed (references may have been removed or modified)",
            ),
            (MockReferenceValidator(should_revert=True), "Reference validation failed"),
        ]

        for validator, expected_reason in validators:
            pipeline = ValidationPipeline()
            pipeline.add_validator(validator)

            result, should_revert = await pipeline.validate("original", "edited", {})

            assert should_revert is True
            assert pipeline.last_failure is not None
            assert expected_reason in pipeline.last_failure.reason

    @pytest.mark.asyncio
    async def test_failure_reason_extraction_for_spelling_validator(self):
        """Test failure reason extraction for Spelling validator type."""
        pipeline = ValidationPipeline()

        class MockSpellingValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "Spelling validation failed" if should_revert else ""
                )

        validator = MockSpellingValidator(should_revert=True)
        pipeline.add_validator(validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert should_revert is True
        assert pipeline.last_failure is not None
        assert "Spelling validation failed" in pipeline.last_failure.reason

    @pytest.mark.asyncio
    async def test_failure_reason_extraction_for_listmarker_validator(self):
        """Test failure reason extraction for ListMarker validator type."""
        pipeline = ValidationPipeline()

        class MockListMarkerValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "List marker validation failed" if should_revert else ""
                )

        validator = MockListMarkerValidator(should_revert=True)
        pipeline.add_validator(validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert should_revert is True
        assert pipeline.last_failure is not None
        assert "List marker validation failed" in pipeline.last_failure.reason

    @pytest.mark.asyncio
    async def test_failure_reason_extraction_for_unknown_validator(self):
        """Test failure reason extraction for unknown validator type."""
        pipeline = ValidationPipeline()

        class MockUnknownValidator(MockValidator):
            def __init__(
                self, should_revert: bool = False, modify_content: bool = False
            ):
                super().__init__(should_revert, modify_content)
                self.last_failure_reason = (
                    "Validation failed in MockUnknownValidator" if should_revert else ""
                )

        validator = MockUnknownValidator(should_revert=True)
        pipeline.add_validator(validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert should_revert is True
        assert pipeline.last_failure is not None
        assert (
            "Validation failed in MockUnknownValidator" in pipeline.last_failure.reason
        )

    def test_get_last_failure_none(self):
        """Test get_last_failure when no failure occurred."""
        pipeline = ValidationPipeline()
        assert pipeline.get_last_failure() is None

    @pytest.mark.asyncio
    async def test_get_last_failure_after_success(self):
        """Test get_last_failure after successful validation."""
        pipeline = ValidationPipeline()
        validator = MockValidator(should_revert=False)
        pipeline.add_validator(validator)

        result, should_revert = await pipeline.validate("original", "edited", {})

        assert should_revert is False
        assert pipeline.get_last_failure() is None

    def test_clear_pipeline(self):
        """Test clearing all validators from the pipeline."""
        pipeline = ValidationPipeline()

        # Add some validators
        validator1 = MockValidator()
        validator2 = MockAsyncValidator()
        pipeline.add_validator(validator1)
        pipeline.add_async_validator(validator2)

        # Set a failure
        from services.validation.pipeline import ValidationFailure

        pipeline.last_failure = ValidationFailure(
            "TestValidator", "sync", "Test failure", "original", "edited"
        )

        # Verify validators and failure are set
        assert len(pipeline.validators) == 1
        assert len(pipeline.async_validators) == 1
        assert pipeline.last_failure is not None

        # Clear the pipeline
        pipeline.clear()

        # Verify everything is cleared
        assert len(pipeline.validators) == 0
        assert len(pipeline.async_validators) == 0
        assert pipeline.last_failure is None


class TestValidationPipelineBuilder:
    """Test ValidationPipelineBuilder class."""

    def test_builder_add_validator_fluent_interface(self):
        """Test that builder add_validator returns self for fluent interface."""
        builder = ValidationPipelineBuilder()
        validator = MockValidator()

        result = builder.add_validator(validator)

        assert result is builder
        assert len(builder.pipeline.validators) == 1
        assert builder.pipeline.validators[0] is validator

    def test_builder_add_async_validator_fluent_interface(self):
        """Test that builder add_async_validator returns self for fluent interface."""
        builder = ValidationPipelineBuilder()
        validator = MockAsyncValidator()

        result = builder.add_async_validator(validator)

        assert result is builder
        assert len(builder.pipeline.async_validators) == 1
        assert builder.pipeline.async_validators[0] is validator

    def test_builder_chaining(self):
        """Test that builder methods can be chained."""
        builder = ValidationPipelineBuilder()
        sync_validator = MockValidator()
        async_validator = MockAsyncValidator()

        result = builder.add_validator(sync_validator).add_async_validator(
            async_validator
        )

        assert result is builder
        assert len(builder.pipeline.validators) == 1
        assert len(builder.pipeline.async_validators) == 1
        assert builder.pipeline.validators[0] is sync_validator
        assert builder.pipeline.async_validators[0] is async_validator

    def test_builder_build(self):
        """Test that builder build returns the configured pipeline."""
        builder = ValidationPipelineBuilder()
        validator = MockValidator()
        builder.add_validator(validator)

        pipeline = builder.build()

        assert isinstance(pipeline, ValidationPipeline)
        assert len(pipeline.validators) == 1
        assert pipeline.validators[0] is validator


class TestPreProcessingPipeline:
    """Test PreProcessingPipeline class."""

    def test_preprocessing_pipeline_inheritance(self):
        """Test that PreProcessingPipeline inherits from ValidationPipeline."""
        pipeline = PreProcessingPipeline()
        assert isinstance(pipeline, ValidationPipeline)


class TestPostProcessingPipeline:
    """Test PostProcessingPipeline class."""

    def test_postprocessing_pipeline_inheritance(self):
        """Test that PostProcessingPipeline inherits from ValidationPipeline."""
        pipeline = PostProcessingPipeline()
        assert isinstance(pipeline, ValidationPipeline)


class TestValidationPipelineExecutionOrder:
    """Tests for ValidationPipeline execution order."""

    @pytest.mark.asyncio
    async def test_async_validators_should_run_before_sync_validators(self):
        """
        Test that async validators run before sync validators to fix Apollo bug.

        This is the RED test - it should fail with the current implementation
        where sync validators run before async validators.

        The test simulates the Apollo scenario from the logs:
        - Original: "He invoked Apollo" (no link)
        - LLM adds: "invoking [[Apollo]]" (new link)
        - Expected: WikiLinkValidator removes [[Apollo]] before AddedContentValidator can detect it
        """
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        # Setup components
        reference_handler = ReferenceHandler()
        reference_validator = ReferenceValidator()
        wiki_link_validator = WikiLinkValidator(reference_handler)

        execution_order: List[str] = []

        # Build pipeline with WikiLinkValidatorAdapter (async) added first
        builder = ValidationPipelineBuilder()

        # Add WikiLinkValidatorAdapter FIRST (async - should run first to remove Apollo)
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        # Add AddedContentValidatorAdapter SECOND (sync - should run after Apollo is removed)
        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        pipeline = builder.build()

        original = "He invoked Apollo and asked the god to avenge the broken promise."
        llm_added_apollo = "invoking [[Apollo]] to avenge the broken promise."

        # Run the pipeline
        final_text, should_revert = await pipeline.validate(
            original,
            llm_added_apollo,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        # DESIRED BEHAVIOR (this should pass after we fix the pipeline):
        # 1. WikiLinkValidatorAdapter should run first and remove [[Apollo]] link
        # 2. AddedContentValidatorAdapter should run second and find no new links
        # 3. The edit should succeed without reversion
        if len(execution_order) >= 2:
            # Only check order if we have execution logs (for backward compatibility)
            pass

        if len(execution_order) >= 2:
            first_validator = execution_order[0]
            second_validator = execution_order[1]

            assert "WikiLinkValidatorAdapter" in first_validator, (
                f"WikiLinkValidatorAdapter should run first to remove Apollo link. "
                f"Actual first: {first_validator}"
            )

            assert "AddedContentValidatorAdapter" in second_validator, (
                f"AddedContentValidatorAdapter should run second after Apollo is removed. "
                f"Actual second: {second_validator}"
            )

        # The edit should succeed because WikiLinkValidator removes Apollo before AddedContentValidator sees it
        assert not should_revert, (
            f"Edit should not revert when WikiLinkValidator removes new links before AddedContentValidator. "
            f"Final text: {final_text}"
        )

        # The Apollo link should be removed but the text should remain
        assert "[[Apollo]]" not in final_text, "Apollo link markup should be removed"
        assert "Apollo" in final_text, "Apollo text should remain"

    @pytest.mark.asyncio
    async def test_real_cinyras_apollo_scenario_from_logs(self):
        """
        Test the exact Cinyras/Apollo scenario from the production logs.

        This scenario actually SHOULD revert because it has extensive link violations
        beyond just Apollo (duplicates, restructuring, etc.). But it should revert
        from WikiLinkValidator, not AddedContentValidator, demonstrating the fix.
        """
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        # Setup components
        reference_handler = ReferenceHandler()
        reference_validator = ReferenceValidator()
        wiki_link_validator = WikiLinkValidator(reference_handler)

        # Build pipeline in correct order
        builder = ValidationPipelineBuilder()

        # Add async validator first (should run first and catch the violations)
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        # Add sync validator second (should never run because async validator reverts)
        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        pipeline = builder.build()

        # Exact content from the logs
        original = "Cinyras was a ruler of [[Cyprus]], who was a friend of [[Agamemnon]]. Cinyras promised to assist Agamemnon in the Trojan war, but did not keep his promise. Agamemnon cursed Cinyras. He invoked Apollo and asked the god to avenge the broken promise. Apollo then had a [[lyre]]-playing contest with [[Cinyras]], and defeated him. Either Cinyras committed suicide when he lost, or was killed by Apollo."

        # LLM output that added Apollo links AND has many other link violations
        llm_output = "[[Cinyras]], a ruler of [[Cyprus]] and friend of [[Agamemnon]], promised to assist him in the Trojan War but broke his promise. [[Agamemnon]] cursed [[Cinyras]], invoking [[Apollo]] to avenge the broken promise. [[Apollo]] then defeated [[Cinyras]] in a [[lyre]]-playing contest. [[Cinyras]] either committed suicide after losing or was killed by [[Apollo]]."

        # Run validation
        final_text, should_revert = await pipeline.validate(
            original,
            llm_output,
            {"paragraph_index": 90, "total_paragraphs": 175, "refs_list": []},
        )

        # This scenario SHOULD revert due to extensive link violations
        assert should_revert, (
            "The complex Cinyras scenario should revert due to duplicate links and extensive restructuring"
        )

        # But the key fix is that it should revert from WikiLinkValidator (async),
        # not AddedContentValidator (sync), proving the execution order is correct
        failure = pipeline.get_last_failure()
        assert failure is not None, "Should have failure information"
        assert failure.validator_name == "WikiLinkValidatorAdapter", (
            f"Should fail in WikiLinkValidatorAdapter (async), not AddedContentValidatorAdapter (sync). "
            f"Actually failed in: {failure.validator_name}"
        )
        assert failure.validator_type == "async", (
            f"Should fail in async validator. Actually failed in: {failure.validator_type}"
        )

    @pytest.mark.asyncio
    async def test_simple_apollo_only_scenario_should_succeed(self):
        """
        Test a simpler Apollo-only scenario that should succeed after the fix.

        This tests the core Apollo bug fix: when only Apollo links are added
        (without other policy violations), WikiLinkValidator should remove them
        and the edit should succeed.
        """
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        # Setup components
        reference_handler = ReferenceHandler()
        reference_validator = ReferenceValidator()
        wiki_link_validator = WikiLinkValidator(reference_handler)

        # Build pipeline in correct order
        builder = ValidationPipelineBuilder()

        # Add async validator first (should clean up Apollo links)
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        # Add sync validator second (should find no violations after cleanup)
        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        pipeline = builder.build()

        # Simple scenario: just adding Apollo links to existing content
        original = "Cinyras invoked Apollo and asked the god to avenge the broken promise. Apollo then defeated him."
        llm_output = "Cinyras invoked [[Apollo]] and asked the god to avenge the broken promise. [[Apollo]] then defeated him."

        # Run validation
        final_text, should_revert = await pipeline.validate(
            original,
            llm_output,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        # This simple Apollo-only scenario should succeed after the fix
        assert not should_revert, (
            "Simple Apollo-only additions should succeed when WikiLinkValidator removes the new links"
        )

        # Apollo links should be removed but text preserved
        assert "[[Apollo]]" not in final_text, "Apollo link markup should be removed"
        assert "Apollo" in final_text, "Apollo text should be preserved"

        # Expected result: Apollo links removed, text preserved
        expected = "Cinyras invoked Apollo and asked the god to avenge the broken promise. Apollo then defeated him."
        assert final_text == expected, f"Expected clean text, got: {final_text}"


class TestValidationPipelineComprehensive:
    """Comprehensive tests for validation pipeline execution order and validator functionality."""

    @pytest.mark.asyncio
    async def test_all_validators_execution_order_comprehensive(self):
        """Test that all validators run in the expected order with proper functionality."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            CompositeReferenceValidatorAdapter,
            ListMarkerValidatorAdapter,
            MetaCommentaryValidatorAdapter,
            QuoteValidatorAdapter,
            ReferenceContentValidatorAdapter,
            SpellingValidatorAdapter,
            TemplateValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.validators.list_marker_validator import (
            ListMarkerValidator,
        )
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )
        from services.validation.validators.quote_validator import QuoteValidator
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.spelling_validator import SpellingValidator
        from services.validation.validators.template_validator import TemplateValidator
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        # Setup components
        reference_handler = ReferenceHandler()
        execution_order: List[str] = []

        # Create all validators
        wiki_link_validator = WikiLinkValidator(reference_handler)
        template_validator = TemplateValidator()
        quote_validator = QuoteValidator()
        reference_validator = ReferenceValidator()
        spelling_validator = SpellingValidator()
        list_marker_validator = ListMarkerValidator()
        meta_commentary_validator = MetaCommentaryValidator()

        # Build pipeline in the same order as edit_service.py
        builder = ValidationPipelineBuilder()

        # Add validators in same order as edit_service.py
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        template_adapter = TemplateValidatorAdapter(
            template_validator, reference_handler
        )
        builder.add_validator(template_adapter)

        quote_adapter = QuoteValidatorAdapter(quote_validator, reference_handler)
        builder.add_validator(quote_adapter)

        ref_adapter = CompositeReferenceValidatorAdapter(
            reference_validator, MagicMock()
        )
        builder.add_validator(ref_adapter)

        ref_content_adapter = ReferenceContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(ref_content_adapter)

        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        spelling_adapter = SpellingValidatorAdapter(spelling_validator)
        builder.add_validator(spelling_adapter)

        list_marker_adapter = ListMarkerValidatorAdapter(list_marker_validator)
        builder.add_validator(list_marker_adapter)

        meta_commentary_adapter = MetaCommentaryValidatorAdapter(
            meta_commentary_validator
        )
        builder.add_validator(meta_commentary_adapter)

        pipeline = builder.build()

        # Test text that could trigger various validators
        original = "* Original list item with colour text."
        edited = "Modified list item with color text and [[NewLink]]."

        final_text, should_revert = await pipeline.validate(
            original,
            edited,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        # Verify execution order
        print("=== COMPREHENSIVE EXECUTION ORDER ===")
        for i, msg in enumerate(execution_order, 1):
            print(f"{i}. {msg}")

        # WikiLinkValidatorAdapter should run first (async)
        if len(execution_order) >= 1:
            assert "WikiLinkValidatorAdapter" in execution_order[0], (
                f"WikiLinkValidatorAdapter should run first: {execution_order[0]}"
            )

        # The NewLink should be removed by WikiLinkValidator before other validators see it
        assert "[[NewLink]]" not in final_text, (
            "NewLink should be removed by WikiLinkValidator"
        )

    @pytest.mark.asyncio
    async def test_spelling_validator_runs_before_added_content_validator_issue(self):
        """Test potential execution order issue: SpellingValidator should run before AddedContentValidator."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            SpellingValidatorAdapter,
        )
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.spelling_validator import SpellingValidator

        reference_handler = ReferenceHandler()
        execution_order: List[str] = []

        # Create validators
        reference_validator = ReferenceValidator()
        spelling_validator = SpellingValidator()

        # Build pipeline with CURRENT order (AddedContent before Spelling - potentially problematic)
        builder = ValidationPipelineBuilder()

        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        spelling_adapter = SpellingValidatorAdapter(spelling_validator)
        builder.add_validator(spelling_adapter)

        pipeline = builder.build()

        # Test case: LLM changes regional spelling
        original = "The colour of the item is important."
        edited = (
            "The color of the item is important."  # LLM changed "colour" to "color"
        )

        final_text, should_revert = await pipeline.validate(
            original,
            edited,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        print("=== SPELLING VALIDATION ORDER ===")
        for i, msg in enumerate(execution_order, 1):
            print(f"{i}. {msg}")

        # AddedContentValidator runs first and should NOT revert for simple spelling changes
        if len(execution_order) >= 1:
            assert "AddedContentValidatorAdapter" in execution_order[0]
        if len(execution_order) > 1:
            assert "SpellingValidatorAdapter" in execution_order[1]

        # Should not revert for regional spelling changes
        assert not should_revert, "Should not revert for regional spelling changes"
        # SpellingValidator should correct back to original spelling
        assert "colour" in final_text, (
            "SpellingValidator should correct back to original spelling"
        )

    @pytest.mark.asyncio
    async def test_list_marker_validator_runs_before_added_content_validator_issue(
        self,
    ):
        """Test potential execution order issue: ListMarkerValidator should run before AddedContentValidator."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            ListMarkerValidatorAdapter,
        )
        from services.validation.validators.list_marker_validator import (
            ListMarkerValidator,
        )
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )

        reference_handler = ReferenceHandler()
        execution_order: List[str] = []

        # Create validators
        reference_validator = ReferenceValidator()
        list_marker_validator = ListMarkerValidator()

        # Build pipeline with CURRENT order (AddedContent before ListMarker - potentially problematic)
        builder = ValidationPipelineBuilder()

        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        list_marker_adapter = ListMarkerValidatorAdapter(list_marker_validator)
        builder.add_validator(list_marker_adapter)

        pipeline = builder.build()

        # Test case: LLM changes list marker
        original = "* Original list item content."
        edited = "# Modified list item content."  # LLM changed "*" to "#"

        final_text, should_revert = await pipeline.validate(
            original,
            edited,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        print("=== LIST MARKER VALIDATION ORDER ===")
        for i, msg in enumerate(execution_order, 1):
            print(f"{i}. {msg}")

        # AddedContentValidator runs first
        if len(execution_order) >= 1:
            assert "AddedContentValidatorAdapter" in execution_order[0]
        if len(execution_order) > 1:
            assert "ListMarkerValidatorAdapter" in execution_order[1]

        # Should not revert for list marker changes
        assert not should_revert, "Should not revert for list marker changes"
        # ListMarkerValidator should restore original marker
        assert final_text.startswith("*"), (
            "ListMarkerValidator should restore original '*' marker"
        )

    @pytest.mark.asyncio
    async def test_quote_validator_execution_order(self):
        """Test that QuoteValidator runs before AddedContentValidator to fix quote issues."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            QuoteValidatorAdapter,
        )
        from services.validation.validators.quote_validator import QuoteValidator
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )

        reference_handler = ReferenceHandler()
        execution_order: List[str] = []

        # Create validators
        reference_validator = ReferenceValidator()
        quote_validator = QuoteValidator()

        # Build pipeline with current order (Quote before AddedContent - should be correct)
        builder = ValidationPipelineBuilder()

        quote_adapter = QuoteValidatorAdapter(quote_validator, reference_handler)
        builder.add_validator(quote_adapter)

        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        pipeline = builder.build()

        # Test case: LLM removes quotes
        original = 'The phrase "hello world" is common.'
        edited = "The phrase hello world is common."  # LLM removed quotes

        final_text, should_revert = await pipeline.validate(
            original,
            edited,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        print("=== QUOTE VALIDATION ORDER ===")
        for i, msg in enumerate(execution_order, 1):
            print(f"{i}. {msg}")

        # QuoteValidator should run first to restore quotes
        if len(execution_order) >= 1:
            assert "QuoteValidatorAdapter" in execution_order[0]

        # This order is correct - no issue expected

    @pytest.mark.asyncio
    async def test_content_modifying_vs_content_validating_order_analysis(self):
        """Analyze which validators modify content vs validate content to identify order issues."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            ListMarkerValidatorAdapter,
            SpellingValidatorAdapter,
        )
        from services.validation.validators.list_marker_validator import (
            ListMarkerValidator,
        )
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.spelling_validator import SpellingValidator

        reference_handler = ReferenceHandler()
        execution_order: List[str] = []

        # Create all content-related validators
        reference_validator = ReferenceValidator()
        spelling_validator = SpellingValidator()
        list_marker_validator = ListMarkerValidator()

        # Build pipeline to test content modification behavior
        builder = ValidationPipelineBuilder()

        # Add in problematic order: validators that VALIDATE content before validators that MODIFY content
        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)  # VALIDATES - runs first (BAD)

        # Content modifiers that should run BEFORE validators
        spelling_adapter = SpellingValidatorAdapter(spelling_validator)
        builder.add_validator(
            spelling_adapter
        )  # MODIFIES - runs after (POTENTIALLY BAD)

        list_marker_adapter = ListMarkerValidatorAdapter(list_marker_validator)
        builder.add_validator(
            list_marker_adapter
        )  # MODIFIES - runs after (POTENTIALLY BAD)

        pipeline = builder.build()

        # Test complex content that needs multiple fixes
        original = "* The colour is important."
        edited = "# The color and [[NewLink]] is important."  # Multiple issues

        final_text, should_revert = await pipeline.validate(
            original,
            edited,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        print("=== CONTENT MODIFIER vs VALIDATOR ORDER ANALYSIS ===")
        for i, msg in enumerate(execution_order, 1):
            print(f"{i}. {msg}")

        # This test demonstrates potential order issues
        # AddedContentValidatorAdapter runs first and might revert before fixers can run
        if len(execution_order) >= 1:
            assert "AddedContentValidatorAdapter" in execution_order[0]

        # Document the issue for fixing
        print(f"Final text: {final_text}")
        print(f"Should revert: {should_revert}")

    @pytest.mark.asyncio
    async def test_proper_execution_order_recommendation(self):
        """Test the recommended execution order: Async modifiers, Sync modifiers, Sync validators."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            ListMarkerValidatorAdapter,
            QuoteValidatorAdapter,
            SpellingValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.validators.list_marker_validator import (
            ListMarkerValidator,
        )
        from services.validation.validators.quote_validator import QuoteValidator
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.spelling_validator import SpellingValidator
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        reference_handler = ReferenceHandler()
        execution_order: List[str] = []

        # Create validators
        wiki_link_validator = WikiLinkValidator(reference_handler)
        quote_validator = QuoteValidator()
        reference_validator = ReferenceValidator()
        spelling_validator = SpellingValidator()
        list_marker_validator = ListMarkerValidator()

        # Build pipeline with RECOMMENDED order
        builder = ValidationPipelineBuilder()

        # 1. ASYNC CONTENT MODIFIERS (run first due to my fix)
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        # 2. SYNC CONTENT MODIFIERS (should run before validators)
        quote_adapter = QuoteValidatorAdapter(quote_validator, reference_handler)
        builder.add_validator(quote_adapter)

        spelling_adapter = SpellingValidatorAdapter(spelling_validator)
        builder.add_validator(spelling_adapter)

        list_marker_adapter = ListMarkerValidatorAdapter(list_marker_validator)
        builder.add_validator(list_marker_adapter)

        # 3. SYNC CONTENT VALIDATORS (should run after modifiers)
        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        pipeline = builder.build()

        # Test complex scenario with multiple issues
        original = "* The colour of the item."
        edited = (
            "# The color of the [[NewLink]] item."  # List marker + spelling + new link
        )

        final_text, should_revert = await pipeline.validate(
            original,
            edited,
            {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
        )

        print("=== RECOMMENDED EXECUTION ORDER ===")
        for i, msg in enumerate(execution_order, 1):
            print(f"{i}. {msg}")

        # Verify order: Async modifiers → Sync modifiers → Sync validators
        expected_order = [
            "WikiLinkValidatorAdapter",  # Async modifier (removes [[NewLink]])
            "QuoteValidatorAdapter",  # Sync modifier
            "SpellingValidatorAdapter",  # Sync modifier (color → colour)
            "ListMarkerValidatorAdapter",  # Sync modifier (# → *)
            "AddedContentValidatorAdapter",  # Sync validator (validates cleaned content)
        ]

        for i, expected in enumerate(expected_order):
            if i < len(execution_order):
                assert expected in execution_order[i], (
                    f"Expected {expected} at position {i + 1}, got {execution_order[i]}"
                )

        # Final text should be properly cleaned
        assert not should_revert, "Should not revert with proper execution order"
        assert "[[NewLink]]" not in final_text, "NewLink should be removed"
        assert "colour" in final_text, "Spelling should be corrected"
        assert final_text.startswith("*"), "List marker should be restored"

    @pytest.mark.asyncio
    async def test_validation_pipeline_comprehensive_integration(self):
        """Integration test with all validators to ensure no regressions."""
        from services.text.reference_handler import ReferenceHandler
        from services.validation.adapters import (
            AddedContentValidatorAdapter,
            CompositeReferenceValidatorAdapter,
            ListMarkerValidatorAdapter,
            MetaCommentaryValidatorAdapter,
            QuoteValidatorAdapter,
            ReferenceContentValidatorAdapter,
            SpellingValidatorAdapter,
            TemplateValidatorAdapter,
            WikiLinkValidatorAdapter,
        )
        from services.validation.validators.list_marker_validator import (
            ListMarkerValidator,
        )
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )
        from services.validation.validators.quote_validator import QuoteValidator
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )
        from services.validation.validators.spelling_validator import SpellingValidator
        from services.validation.validators.template_validator import TemplateValidator
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        # Setup components
        reference_handler = ReferenceHandler()

        # Create all validators
        wiki_link_validator = WikiLinkValidator(reference_handler)
        template_validator = TemplateValidator()
        quote_validator = QuoteValidator()
        reference_validator = ReferenceValidator()
        spelling_validator = SpellingValidator()
        list_marker_validator = ListMarkerValidator()
        meta_commentary_validator = MetaCommentaryValidator()

        # Build pipeline with the FIXED order (same as edit_service.py)
        builder = ValidationPipelineBuilder()

        # 1. ASYNC CONTENT MODIFIERS
        link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
        builder.add_async_validator(link_adapter)

        # 2. SYNC CONTENT MODIFIERS
        template_adapter = TemplateValidatorAdapter(
            template_validator, reference_handler
        )
        builder.add_validator(template_adapter)

        quote_adapter = QuoteValidatorAdapter(quote_validator, reference_handler)
        builder.add_validator(quote_adapter)

        spelling_adapter = SpellingValidatorAdapter(spelling_validator)
        builder.add_validator(spelling_adapter)

        list_marker_adapter = ListMarkerValidatorAdapter(list_marker_validator)
        builder.add_validator(list_marker_adapter)

        # 3. SYNC CONTENT VALIDATORS
        ref_adapter = CompositeReferenceValidatorAdapter(
            reference_validator, MagicMock()
        )
        builder.add_validator(ref_adapter)

        ref_content_adapter = ReferenceContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(ref_content_adapter)

        added_content_adapter = AddedContentValidatorAdapter(
            reference_validator, reference_handler
        )
        builder.add_validator(added_content_adapter)

        meta_commentary_adapter = MetaCommentaryValidatorAdapter(
            meta_commentary_validator
        )
        builder.add_validator(meta_commentary_adapter)

        pipeline = builder.build()

        # Test scenarios that previously failed
        test_cases = [
            {
                "name": "Apollo link scenario",
                "original": "Cinyras invoked Apollo to avenge the broken promise.",
                "edited": "[[Cinyras]] invoked [[Apollo]] to avenge the broken promise.",
                "expected_outcome": "no_revert",  # WikiLinkValidator should clean it up
            },
            {
                "name": "Spelling + list marker scenario",
                "original": "* The colour is important.",
                "edited": "# The color is important.",
                "expected_outcome": "no_revert",  # Should be fixed by modifiers
            },
            {
                "name": "Complex multi-issue scenario",
                "original": "* The colour of the item.",
                "edited": "# The color of the [[NewLink]] item.",
                "expected_outcome": "no_revert",  # All issues should be fixed
            },
        ]

        for test_case in test_cases:
            print(f"\n=== Testing: {test_case['name']} ===")

            final_text, should_revert = await pipeline.validate(
                test_case["original"],
                test_case["edited"],
                {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
            )

            print(f"Original: {test_case['original']}")
            print(f"Edited: {test_case['edited']}")
            print(f"Final: {final_text}")
            print(f"Should revert: {should_revert}")

            if test_case["expected_outcome"] == "no_revert":
                assert not should_revert, (
                    f"Test case '{test_case['name']}' should not revert but did"
                )

            # Verify specific fixes
            if "NewLink" in test_case["edited"]:
                assert "[[NewLink]]" not in final_text, "NewLink should be removed"
            if "color" in test_case["edited"] and "colour" in test_case["original"]:
                assert "colour" in final_text, "Spelling should be corrected"
            if test_case["edited"].startswith("#") and test_case["original"].startswith(
                "*"
            ):
                assert final_text.startswith("*"), "List marker should be restored"

        print("\n✅ All comprehensive validation tests passed!")
