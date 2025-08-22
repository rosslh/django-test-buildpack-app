"""Validation pipeline for chaining validators together.

This module implements a pipeline pattern that allows validators to be composed and
executed in sequence, following the Open/Closed Principle.
"""

from enum import Enum, auto
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from services.core.interfaces import (
    IAsyncValidator,
    IValidationPipeline,
    IValidator,
)


class ValidationResult(Enum):
    """Result of a validation operation."""

    SUCCESS = auto()
    REVERT = auto()
    MODIFIED = auto()


class ValidationFailure(NamedTuple):
    """Information about a validation failure."""

    validator_name: str
    validator_type: str  # 'sync' or 'async'
    reason: str
    original_content: str
    edited_content: str


class ValidationPipeline(IValidationPipeline):
    """A pipeline that chains multiple validators together.

    Validators are executed in the order they were added. If any validator returns a
    revert signal, the pipeline stops and returns the revert.
    """

    def __init__(self):
        self.validators: List[IValidator] = []
        self.async_validators: List[IAsyncValidator] = []
        self.last_failure: Optional[ValidationFailure] = None

    def add_validator(self, validator: IValidator) -> None:
        """Add a synchronous validator to the pipeline."""
        self._add_validator(validator, self.validators, "validator")

    def add_async_validator(self, validator: IAsyncValidator) -> None:
        """Add an asynchronous validator to the pipeline."""
        self._add_validator(validator, self.async_validators, "async validator")

    def _add_validator(
        self, validator: Any, validator_list: List[Any], validator_type: str
    ) -> None:
        """Helper to add a validator to a list."""
        validator_list.append(validator)

    def get_last_failure(self) -> Optional[ValidationFailure]:
        """Get information about the last validation failure."""
        return self.last_failure

    async def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Run all validators in the pipeline.

        Args:
            original: Original content
            edited: Edited content to validate
            context: Validation context

        Returns:
            Tuple of (processed_content, should_revert)
        """
        current_content = edited
        self.last_failure = None

        # Run async validators first (they can modify content, e.g., remove newly added links)
        for async_validator in self.async_validators:
            current_content, should_revert = await async_validator.validate(
                original, current_content, context
            )

            if should_revert:
                # Capture detailed failure information
                failure_reason = (
                    async_validator.get_last_failure_reason()
                    or f"Async validation failed in {async_validator.__class__.__name__}"
                )
                self.last_failure = ValidationFailure(
                    validator_name=async_validator.__class__.__name__,
                    validator_type="async",
                    reason=failure_reason,
                    original_content=original,
                    edited_content=current_content,
                )

                return current_content, True

        # Then run synchronous validators (they validate the cleaned content)
        for validator in self.validators:
            current_content, should_revert = validator.validate(
                original, current_content, context
            )

            if should_revert:
                # Capture detailed failure information
                failure_reason = (
                    validator.get_last_failure_reason()
                    or f"Validation failed in {validator.__class__.__name__}"
                )
                self.last_failure = ValidationFailure(
                    validator_name=validator.__class__.__name__,
                    validator_type="sync",
                    reason=failure_reason,
                    original_content=original,
                    edited_content=current_content,
                )

                return current_content, True

        return current_content, False

    def clear(self) -> None:
        # TODO: is this method needed?
        """Clear all validators from the pipeline."""
        self.validators.clear()
        self.async_validators.clear()
        self.last_failure = None


class PreProcessingPipeline(ValidationPipeline):
    """Pipeline for pre-processing validations (before LLM)."""


class PostProcessingPipeline(ValidationPipeline):
    """Pipeline for post-processing validations (after LLM)."""


class ValidationPipelineBuilder:
    """Builder for creating validation pipelines with a fluent interface.

    This follows the Builder pattern to make pipeline construction more readable.
    """

    def __init__(self):
        self.pipeline = ValidationPipeline()

    def add_validator(self, validator: IValidator) -> "ValidationPipelineBuilder":
        """Add a validator to the pipeline."""
        self.pipeline.add_validator(validator)
        return self

    def add_async_validator(
        self, validator: IAsyncValidator
    ) -> "ValidationPipelineBuilder":
        """Add an async validator to the pipeline."""
        self.pipeline.add_async_validator(validator)
        return self

    def build(self) -> ValidationPipeline:
        """Build and return the configured pipeline."""
        return self.pipeline
