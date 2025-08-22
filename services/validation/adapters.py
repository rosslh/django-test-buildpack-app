"""Adapters for existing validators to work with the new interface.

This module provides adapter classes that wrap existing validators to make them
compatible with the IValidator and IAsyncValidator interfaces.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from services.core.interfaces import (
    IAsyncValidator,
    IReferenceHandler,
    IValidator,
)
from services.tracking.reversion_tracker import ReversionType
from services.validation.validators.list_marker_validator import ListMarkerValidator
from services.validation.validators.quote_validator import QuoteValidator
from services.validation.validators.reference_validator import ReferenceValidator
from services.validation.validators.spelling_validator import SpellingValidator
from services.validation.validators.template_validator import TemplateValidator
from services.validation.validators.wiki_link_validator import WikiLinkValidator

if TYPE_CHECKING:
    from services.validation.validators.meta_commentary_validator import (
        MetaCommentaryValidator,
    )


class WikiLinkValidatorAdapter(IAsyncValidator):
    """Adapter for WikiLinkValidator to implement IAsyncValidator interface."""

    def __init__(self, validator: WikiLinkValidator):
        self.validator = validator
        self.last_failure_reason: Optional[str] = None

    async def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate wikilinks using the wrapped validator."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)

        # Call the original validator method, passing original as original_paragraph_content
        (
            result_text,
            should_revert,
        ) = await self.validator.validate_and_reintroduce_links(
            original_paragraph_content=original,
            edited_text_with_placeholders=edited,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        if should_revert:
            self.last_failure_reason = "Links were added, removed, or modified in a way that violates link policies"

        return result_text, should_revert

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class TemplateValidatorAdapter(IValidator):
    """Adapter for TemplateValidator to implement IValidator interface."""

    def __init__(
        self,
        validator: TemplateValidator,
        reference_handler: IReferenceHandler,
    ):
        self.validator = validator
        self.reference_handler = reference_handler
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate templates using the wrapped validator."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)
        refs_list = context.get("refs_list", [])

        original_for_validation = self.reference_handler.restore_references(
            original, refs_list
        )
        edited_for_validation = self.reference_handler.restore_references(
            edited, refs_list
        )

        should_revert = self.validator.validate(
            original_text=original_for_validation,
            edited_text=edited_for_validation,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        if should_revert:
            self.last_failure_reason = (
                "One or more templates were removed, added, or modified"
            )
            return original, True

        return edited, False

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class ReferenceValidatorAdapter(IValidator):
    """Adapter for ReferenceValidator to implement IValidator interface."""

    def __init__(self, validator: ReferenceValidator):
        self.validator = validator
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate references using the wrapped validator."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)

        # Check for removed references
        should_revert = self.validator.validate_references(
            original_paragraph_content=original,
            edited_text_with_placeholders=edited,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        if should_revert:
            self.last_failure_reason = "One or more references were removed or altered"
            return original, True

        return edited, False

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class SpellingValidatorAdapter(IValidator):
    """Adapter for SpellingValidator to implement IValidator interface."""

    def __init__(self, validator: SpellingValidator):
        self.validator = validator
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Correct spelling using the wrapped validator."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)

        try:
            # Apply spelling corrections
            corrected_text = self.validator.correct_regional_spellings(
                original_paragraph_content=original,
                final_edited_text=edited,
                paragraph_index=paragraph_index,
                total_paragraphs=total_paragraphs,
            )

            # Spelling validator doesn't trigger reverts, it just corrects
            return corrected_text, False
        except Exception:
            # On error, revert to original
            self.last_failure_reason = "Spelling correction failed due to an exception"
            return original, True

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class MetaCommentaryValidatorAdapter(IValidator):
    """Adapter for MetaCommentaryValidator to implement IValidator interface."""

    def __init__(self, validator: "MetaCommentaryValidator"):
        self.validator = validator
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate that edits don't contain meta commentary."""
        # Our validator already implements the interface correctly
        result, should_revert = self.validator.validate(original, edited, context)

        if should_revert:
            self.last_failure_reason = self.validator.get_last_failure_reason()

        return result, should_revert

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason or self.validator.get_last_failure_reason()


class ListMarkerValidatorAdapter(IValidator):
    """Adapter for ListMarkerValidator to implement IValidator interface."""

    def __init__(self, validator: ListMarkerValidator):
        self.validator = validator
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate and restore list markers using the wrapped validator."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)

        # Restore list markers if needed
        corrected_text = self.validator.validate_and_restore_list_markers(
            original_paragraph_content=original,
            edited_text=edited,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        # List marker validator doesn't trigger reverts, it just corrects
        return corrected_text, False

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class ReferenceContentValidatorAdapter(IValidator):
    """Adapter for validating reference content changes."""

    def __init__(
        self,
        validator: ReferenceValidator,
        reference_handler: IReferenceHandler,
    ):
        self.validator = validator
        self.reference_handler = reference_handler
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate reference content changes."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)
        refs_list = context.get("refs_list", [])

        # Restore references for internal validation only
        original_for_validation = original
        edited_for_validation = edited
        if refs_list:
            original_for_validation = self.reference_handler.restore_references(
                original, refs_list
            )
            edited_for_validation = self.reference_handler.restore_references(
                edited, refs_list
            )

        # Check for reference content changes
        should_revert = self.validator.validate_reference_content_changes(
            original_paragraph_content=original_for_validation,
            final_edited_text=edited_for_validation,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        if should_revert:
            self.last_failure_reason = (
                "Reference content was modified (content within <ref> tags was changed)"
            )
            return original, True

        return edited, False

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class AddedContentValidatorAdapter(IValidator):
    """Adapter for validating added content."""

    def __init__(
        self,
        validator: ReferenceValidator,
        reference_handler: IReferenceHandler,
    ):
        self.validator = validator
        self.reference_handler = reference_handler
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate that no new content was added."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)
        refs_list = context.get("refs_list", [])

        # Restore references for internal validation only
        original_for_validation = original
        edited_for_validation = edited
        if refs_list:
            original_for_validation = self.reference_handler.restore_references(
                original, refs_list
            )
            edited_for_validation = self.reference_handler.restore_references(
                edited, refs_list
            )

        # Check for added content
        should_revert = self.validator.validate_added_content(
            original_paragraph_content=original_for_validation,
            final_edited_text=edited_for_validation,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        if should_revert:
            failure_reason = self._determine_what_was_added(
                original_for_validation, edited_for_validation
            )
            self.last_failure_reason = failure_reason
            return original, True

        return edited, False

    def _determine_what_was_added(self, original: str, edited: str) -> str:
        """Determine what type of content was added."""
        try:
            import wikitextparser as wtp

            original_parsed = wtp.parse(original)
            edited_parsed = wtp.parse(edited)

            # Check for added links
            original_targets = {str(link.target) for link in original_parsed.wikilinks}
            edited_targets = {str(link.target) for link in edited_parsed.wikilinks}
            new_links = edited_targets - original_targets

            # Check for added references
            original_refs = len(original_parsed.get_tags("ref"))
            edited_refs = len(edited_parsed.get_tags("ref"))

            reasons = []
            if new_links:
                reasons.append(f"New wikilinks added: {', '.join(new_links)}")
            if edited_refs > original_refs:
                reasons.append(
                    f"New reference tags added ({edited_refs - original_refs} new refs)"
                )

            if reasons:
                return "; ".join(reasons)
            else:
                return "New content was added (could not determine specific type)"

        except Exception:
            return "New content was added (error analyzing changes)"

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class CompositeReferenceValidatorAdapter(IValidator):
    """Composite adapter that combines multiple reference validation checks.

    This adapter runs multiple reference-related validations in sequence.
    """

    def __init__(
        self,
        reference_validator: ReferenceValidator,
        reversion_tracker: Any,
    ):
        self.reference_validator = reference_validator
        self.reversion_tracker = reversion_tracker
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Run multiple reference validations."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)
        refs_list = context.get("refs_list", [])

        # First check if this is dealing with placeholders
        if refs_list and any(
            f'<ref name="{i}" />' in edited for i in range(len(refs_list))
        ):
            # Check for removed references
            should_revert = self.reference_validator.validate_references(
                original_paragraph_content=original,
                edited_text_with_placeholders=edited,
                paragraph_index=paragraph_index,
                total_paragraphs=total_paragraphs,
            )

            if should_revert:
                self.reversion_tracker.record_reversion(
                    ReversionType.REFERENCE_VALIDATION_FAILURE
                )

                # Determine specific reason for failure
                self.last_failure_reason = self._determine_reference_failure_reason(
                    original, edited, refs_list
                )

                return original, True

        return edited, False

    def _determine_reference_failure_reason(
        self, original: str, edited: str, refs_list: list
    ) -> str:
        """Determine the specific reason for reference validation failure."""
        try:
            # Count reference placeholders in edited text
            placeholder_count = sum(
                1 for i in range(len(refs_list)) if f'<ref name="{i}" />' in edited
            )

            # Count references in original using the same extraction logic
            original_ref_map = self.reference_validator._extract_reference_placeholders(
                original
            )
            ref_count_original = len(original_ref_map)

            if placeholder_count == 0 and ref_count_original > 0:
                return "All references were removed from the text"
            elif placeholder_count < ref_count_original:
                missing_count = ref_count_original - placeholder_count
                return f"{missing_count} reference(s) were removed from the text"
            else:
                return "Reference placeholders were modified or corrupted"

        except Exception:
            return "Reference validation failed (unable to determine specific cause)"

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason


class QuoteValidatorAdapter(IValidator):
    """Adapter for QuoteValidator to implement IValidator interface."""

    def __init__(
        self,
        validator: "QuoteValidator",
        reference_handler: IReferenceHandler,
    ):
        self.validator = validator
        self.reference_handler = reference_handler
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate quotes using the wrapped validator."""
        paragraph_index = context.get("paragraph_index", 0)
        total_paragraphs = context.get("total_paragraphs", 1)
        refs_list = context.get("refs_list", [])

        # Restore references before validation
        original_for_validation = self.reference_handler.restore_references(
            original, refs_list
        )
        edited_for_validation = self.reference_handler.restore_references(
            edited, refs_list
        )

        (
            corrected_text_full,
            should_revert,
        ) = self.validator.validate_and_correct(
            original_text=original_for_validation,
            edited_text=edited_for_validation,
            paragraph_index=paragraph_index,
            total_paragraphs=total_paragraphs,
        )

        if should_revert:
            self.last_failure_reason = "Quotes were added, removed, or modified in a way that could not be automatically corrected."
            # The validator returns the original text on revert
            return original, True

        # If corrected, we need to convert back to placeholders
        corrected_text_placeholders, _ = (
            self.reference_handler.replace_references_with_placeholders(
                corrected_text_full
            )
        )

        return corrected_text_placeholders, False

    def get_last_failure_reason(self) -> Optional[str]:
        """Get the reason for the last validation failure."""
        return self.last_failure_reason
