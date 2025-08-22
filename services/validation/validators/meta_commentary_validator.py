"""Validator for detecting meta commentary in LLM responses.

This validator catches when the LLM returns meta-commentary instead of actual edits,
such as "I could not identify any changes needed" or similar responses.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from services.core.constants import META_COMMENTARY_WORDS
from services.core.interfaces import IValidator


class MetaCommentaryValidator(IValidator):
    """Validates that edits don't contain meta commentary from the LLM.

    This validator rejects edits that contain words like "I", "me", "edit", "please",
    or "wikitext" when these words don't appear in the original text. This prevents
    the LLM from returning meta-commentary instead of actual edits.
    """

    def __init__(self):
        self.last_failure_reason: Optional[str] = None

    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate that the edited text doesn't contain meta commentary.

        Args:
            original: Original content
            edited: Edited content to validate
            context: Additional context for validation

        Returns:
            Tuple of (processed_content, should_revert)
        """
        self.last_failure_reason = None

        # Extract words from both texts (case-insensitive, word boundaries)
        original_words = self._extract_words(original.lower())
        edited_words_lower = self._extract_words(edited.lower())

        # Find meta commentary words in edited text that aren't in original
        meta_words_in_edited = edited_words_lower.intersection(META_COMMENTARY_WORDS)
        meta_words_in_original = original_words.intersection(META_COMMENTARY_WORDS)

        # Only problematic if meta commentary words appear in edited but not original
        problematic_words = meta_words_in_edited - meta_words_in_original

        if problematic_words:
            # Get the original case words from the edited text
            original_case_words = self._get_original_case_words(
                edited, problematic_words
            )
            word_list = ", ".join(f"'{word}'" for word in sorted(original_case_words))
            self.last_failure_reason = (
                f"Edit contains meta commentary words ({word_list}) "
                f"that don't appear in the original text"
            )

            return original, True

        return edited, False

    def get_last_failure_reason(self) -> Optional[str]:
        """Return the reason for the last validation failure."""
        return self.last_failure_reason

    def _extract_words(self, text: str) -> set:
        """Extract words from text using word boundaries.

        Args:
            text: Text to extract words from (should be lowercase)

        Returns:
            Set of words found in the text
        """
        # Use regex to find whole words only
        words = re.findall(r"\b\w+\b", text)
        return set(words)

    def _get_original_case_words(self, text: str, problematic_words: set) -> List[str]:
        """Get the original case words from the text.

        Args:
            text: Original text with original case
            problematic_words: Set of lowercase problematic words

        Returns:
            List of words in their original case
        """
        # Find all words in the text with their original case
        all_words = re.findall(r"\b\w+\b", text)
        original_case_words = []

        for word in all_words:
            if word.lower() in problematic_words:
                original_case_words.append(word)

        # Remove duplicates while preserving order
        seen = set()
        unique_words = []
        for word in original_case_words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)

        return unique_words
