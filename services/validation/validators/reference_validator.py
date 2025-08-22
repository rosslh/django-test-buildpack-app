"""Validator for handling references."""

import re
from typing import Dict

import wikitextparser as wtp

from services.validation.base_validator import BaseValidator


class ReferenceRemovedError(ValueError):
    """Custom exception for when a reference tag is removed."""


class ReferenceValidator(BaseValidator):
    """Handles validation of reference tags."""

    def validate_references(
        self,
        original_paragraph_content: str,
        edited_text_with_placeholders: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> bool:
        """Validate that no references were removed.

        This method checks if any reference placeholders are missing from the edited
        text compared to the original. It returns True if a revert is needed.
        """
        original_ref_map = self._extract_reference_placeholders(
            original_paragraph_content
        )
        return self._check_removed_references(
            original_ref_map, edited_text_with_placeholders
        )

    def _extract_reference_placeholders(self, content: str) -> Dict[str, str]:
        """Extracts reference placeholders into a map, handling both self-closing and paired tags."""
        # Match both <ref name="..." /> and <ref name="...">...</ref>
        ref_pattern = re.compile(
            r'<ref name="(\d+)"\s*/?>',
            re.IGNORECASE,
        )
        return dict.fromkeys(ref_pattern.findall(content), "")

    def _check_removed_references(
        self, original_ref_map: Dict[str, str], edited_text: str
    ) -> bool:
        """Check for removed references.

        Returns True if a reference was removed, False otherwise.
        """
        for ref_name in original_ref_map.keys():
            if ref_name not in edited_text:
                return True
        return False

    def validate_added_content(
        self,
        original_paragraph_content: str,
        final_edited_text: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> bool:
        """Validate that no new content (links or references) was added."""
        try:
            # Normalize by removing placeholders and extra spaces for a cleaner diff
            original_for_compare = original_paragraph_content.replace(
                " " * 2, " "
            ).replace("()", "")
            edited_for_compare = final_edited_text.replace(" " * 2, " ").replace(
                "()", ""
            )

            original_parsed = wtp.parse(original_for_compare)
            edited_parsed = wtp.parse(edited_for_compare)

            return self._check_added_links(
                original_parsed, edited_parsed
            ) or self._check_added_references(original_parsed, edited_parsed)
        except Exception:
            return True

    def _normalize_target_for_comparison(self, target: str) -> str:
        """Normalize a link target for case-insensitive comparison."""
        return target.lower()

    def _check_added_links(
        self, original_parsed: wtp.WikiText, edited_parsed: wtp.WikiText
    ) -> bool:
        """Check for added wikilinks using case-insensitive comparison."""
        # Get original targets and create normalized mapping
        original_targets = {str(link.target) for link in original_parsed.wikilinks}
        original_normalized = {
            self._normalize_target_for_comparison(target) for target in original_targets
        }

        # Get edited targets and check for truly new ones (case-insensitive)
        edited_targets = {str(link.target) for link in edited_parsed.wikilinks}
        edited_normalized = {
            self._normalize_target_for_comparison(target) for target in edited_targets
        }

        # Find targets that are genuinely new (not just case variations)
        newly_added_normalized = edited_normalized - original_normalized

        if newly_added_normalized:
            return True
        return False

    def _check_added_references(
        self, original_parsed: wtp.WikiText, edited_parsed: wtp.WikiText
    ) -> bool:
        """Check for added reference tags."""
        if len(edited_parsed.get_tags("ref")) > len(original_parsed.get_tags("ref")):
            return True
        return False

    def validate_reference_content_changes(
        self,
        original_paragraph_content: str,
        final_edited_text: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> bool:
        """Validates changes to reference content.

        Returns True if paragraph should be reverted due to invalid changes.
        """
        original_parsed: wtp.WikiText = wtp.parse(original_paragraph_content)
        edited_parsed: wtp.WikiText = wtp.parse(final_edited_text)

        # Allow empty references to be filled (e.g., <ref name="..."/> to <ref name="...">...</ref>)
        # Apply the same filtering to both original and edited to ensure
        # consistent comparison
        original_refs_with_content = [
            r for r in original_parsed.get_tags("ref") if r.contents.strip()
        ]
        edited_refs_with_content = [
            r for r in edited_parsed.get_tags("ref") if r.contents.strip()
        ]

        original_refs_map = self._create_ref_content_map(original_refs_with_content)
        edited_refs_map = self._create_ref_content_map(edited_refs_with_content)

        return self._check_reference_content_changes(original_refs_map, edited_refs_map)

    def _create_ref_content_map(self, ref_tags: list) -> dict:
        """Create a map from reference name/full tag to its content."""
        refs_map = {}
        for ref in ref_tags:
            name = ref.get_attr("name")
            key = name if name else str(ref)
            refs_map[key] = ref.contents.strip()
        return refs_map

    def _check_reference_content_changes(
        self, original_refs_map: Dict[str, str], edited_refs_map: Dict[str, str]
    ) -> bool:
        """Check for disallowed changes in reference content.

        This method checks for changes in the content of reference tags.
        """
        for key, original_content in original_refs_map.items():
            if key not in edited_refs_map:
                return True
            if original_content and original_content != edited_refs_map[key]:
                return True
        return False
