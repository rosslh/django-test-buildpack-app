from collections import Counter

import wikitextparser as wtp

from services.validation.base_validator import BaseValidator


class TemplateValidator(BaseValidator):
    """Handles validation of wikitext templates."""

    def validate(
        self,
        original_text: str,
        edited_text: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> bool:
        """Validate that templates have not been removed, added or modified.

        Returns True if a revert is needed.
        """
        original_parsed = wtp.parse(original_text)
        edited_parsed = wtp.parse(edited_text)

        original_templates = [str(t).strip() for t in original_parsed.templates]
        edited_templates = [str(t).strip() for t in edited_parsed.templates]

        if Counter(original_templates) != Counter(edited_templates):
            original_counts = Counter(original_templates)
            edited_counts = Counter(edited_templates)

            removed = list((original_counts - edited_counts).elements())
            added = list((edited_counts - original_counts).elements())

            if removed or added:
                message = "WARNING: Templates were modified."
                if removed:
                    message += f" Removed: {removed}"
                if added:
                    message += f" Added: {added}"
                message += ". Reverting."
                return True

        return False
