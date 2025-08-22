"""Validator for handling list markers."""

import re
from typing import Optional

from services.validation.base_validator import BaseValidator

LIST_MARKER_PATTERN = r"^(\*+|#+|;)"
LIST_MARKER_WITH_SPACING_PATTERN = r"^(\*+|#+|;)(\s*)"


class ListMarkerValidator(BaseValidator):
    """Handles validation and restoration of list markers."""

    def validate_and_restore_list_markers(
        self,
        original_paragraph_content: str,
        edited_text: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> str:
        """Validates and restores original list markers if they were altered."""
        original_marker_full = self._extract_marker_with_spacing(
            original_paragraph_content
        )
        edited_marker_full = self._extract_marker_with_spacing(edited_text)

        if original_marker_full is None:
            # Original text had no list marker
            if edited_marker_full is not None:
                # But edited text has a list marker - remove it
                edited_len = len(edited_marker_full)
                content_part = edited_text[edited_len:].lstrip()
                return content_part
            return edited_text  # Neither has list markers

        original_marker = self._extract_list_marker(original_marker_full)

        # Handle case where edited text might not have a marker
        edited_marker = None
        if edited_marker_full is not None:
            edited_marker = self._extract_list_marker(edited_marker_full)

        # Restore if the marker type was changed (e.g., '*' to '#')
        if original_marker and edited_marker and original_marker != edited_marker:
            return self._restore_list_marker(
                original_paragraph_content,
                edited_text,
                original_marker,
                edited_marker,
            )

        # Restore if spacing was altered
        if original_marker_full != edited_marker_full:
            # Strip potential leading space from content part of edited_text
            edited_len = (
                len(edited_marker_full) if edited_marker_full is not None else 0
            )
            content_part = edited_text[edited_len:].lstrip()
            return original_marker_full + content_part

        return edited_text

    def _restore_list_marker(
        self,
        original_content: str,
        edited_text: str,
        original_marker: str,
        edited_marker: str,
    ) -> str:
        """Restores the original list marker."""
        # Attempt to find the start of the content after the marker
        match = re.search(LIST_MARKER_WITH_SPACING_PATTERN, edited_text)
        if match:
            # Reconstruct with original marker and spacing, and the new content
            original_spacing = ""
            original_match = re.search(
                LIST_MARKER_WITH_SPACING_PATTERN, original_content
            )
            if original_match:
                original_spacing = original_match.group(2)

            content_start_index = match.end(0)
            content_part = edited_text[content_start_index:].lstrip()
            return original_marker + original_spacing + content_part
        return original_content  # Fallback to original if something goes wrong

    def _extract_list_marker(self, text: str) -> Optional[str]:
        """Extracts the list marker characters (e.g., '*', '#') from a string."""
        match = re.search(LIST_MARKER_PATTERN, text.lstrip())
        if match:
            return match.group(1)
        return None

    def _extract_marker_with_spacing(self, text: str) -> Optional[str]:
        """Extracts list marker with its subsequent spacing."""
        match = re.match(LIST_MARKER_WITH_SPACING_PATTERN, text)
        if match:
            return match.group(0)
        return None
