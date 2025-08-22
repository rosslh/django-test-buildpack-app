"""Validator for handling spelling."""

import re
from typing import Dict, List, Tuple

from services.utils.spelling_utils import find_regional_spelling_changes
from services.validation.base_validator import BaseValidator

WORD_BOUNDARY_PATTERN = r"\b"


class SpellingValidator(BaseValidator):
    """Handles spelling corrections."""

    def correct_regional_spellings(
        self,
        original_paragraph_content: str,
        final_edited_text: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> str:
        """Corrects regional spelling changes introduced by the LLM."""
        spelling_changes = find_regional_spelling_changes(
            original_paragraph_content, final_edited_text
        )

        if not spelling_changes:
            return final_edited_text

        unique_corrections = self._get_unique_corrections(spelling_changes)
        corrected_text, num_replacements = self._apply_spelling_corrections(
            final_edited_text, unique_corrections
        )

        return corrected_text

    def _get_unique_corrections(
        self, spelling_changes: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Return a list of unique spelling corrections."""
        seen = set()
        unique_corrections = []
        for change in spelling_changes:
            # Create a tuple of the items to check for uniqueness
            change_tuple = tuple(sorted(change.items()))
            if change_tuple not in seen:
                seen.add(change_tuple)
                unique_corrections.append(change)
        return unique_corrections

    def _apply_spelling_corrections(
        self, text: str, corrections: List[Dict[str, str]]
    ) -> Tuple[str, int]:
        """Apply spelling corrections to the text."""
        num_replacements = [0]  # Use a list to allow modification in nested function

        def create_replacer(original_word):
            def replacer(match_obj):
                """Case-preserving replacer function."""
                matched_text = match_obj.group(0)
                # Preserve the case of the matched text when replacing
                replacement = self._preserve_case(original_word, matched_text)
                if replacement != matched_text:
                    num_replacements[0] += 1
                return replacement

            return replacer

        for correction in corrections:
            edited_word = correction["edited_word"]
            original_word = correction["original_word"]
            pattern = (
                WORD_BOUNDARY_PATTERN + re.escape(edited_word) + WORD_BOUNDARY_PATTERN
            )
            text = re.sub(
                pattern, create_replacer(original_word), text, flags=re.IGNORECASE
            )

        return text, num_replacements[0]

    def _preserve_case(self, original_word: str, matched_text: str) -> str:
        """Preserve the case of the matched text."""
        if matched_text.isupper():
            return original_word.upper()
        if matched_text.islower():
            return original_word.lower()
        if matched_text.istitle():
            return original_word.title()

        # Handle mixed case: match each character's case if possible
        def match_case(src, template):
            return "".join(
                c.upper() if t.isupper() else c.lower()
                for c, t in zip(src, template, strict=False)
            ) + (src[len(template) :] if len(src) > len(template) else "")

        return match_case(original_word, matched_text)
