"""Reference handling for Wiki editing operations.

This module consolidates all reference-related functionality, including replacing
references with placeholders and restoring them.
"""

import re
from typing import List, Tuple

from services.core.interfaces import IReferenceHandler


class ReferenceHandler(IReferenceHandler):
    """Handles all reference-related operations for wiki text."""

    def replace_references_with_placeholders(self, text: str) -> Tuple[str, List[str]]:
        """Replaces <ref>...</ref> tags with placeholders and returns the modified text and references.

        Args:
            text: The text containing reference tags.

        Returns:
            A tuple of (text_with_placeholders, list_of_extracted_references).
        """
        ref_pattern = re.compile(
            r"(<ref(?: [^>]*)?>.*?</ref>|<ref [^>]*?/>)", re.IGNORECASE | re.DOTALL
        )
        references: List[str] = []

        def replacer(match) -> str:
            placeholder = f'<ref name="{len(references)}" />'
            references.append(match.group(0))
            return placeholder

        text_with_placeholders = ref_pattern.sub(replacer, text)
        return text_with_placeholders, references

    def restore_references(
        self, text_with_placeholders: str, references: List[str]
    ) -> str:
        """Restores <ref>...</ref> tags from placeholders.

        Args:
            text_with_placeholders: Text containing placeholder references.
            references: List of original reference content.

        Returns:
            Text with references restored.
        """
        result = text_with_placeholders

        for i, ref_content in enumerate(references):
            # Handle XML format placeholders
            xml_placeholder = f'<ref name="{i}" />'

            # Replace XML format placeholders
            if xml_placeholder in result:
                result = result.replace(xml_placeholder, ref_content, 1)

        return result
