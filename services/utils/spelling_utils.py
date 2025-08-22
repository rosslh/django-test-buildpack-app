"""Spelling-related utilities.

This module contains functions for handling spelling variations, particularly regional
spelling differences.
"""

import difflib
import re
from typing import Dict, List, Optional

from services.core.data_constants import UK_TO_US_SPELLINGS, US_TO_UK_SPELLINGS


def _tokenize_for_spelling_check(text: Optional[str]) -> List[str]:
    """Tokenizes text for spelling check.

    - Converts to lowercase
    - Splits by non-alphanumeric characters (preserving intra-word hyphens/apostrophes)
    - Removes empty strings

    Args:
        text: The text to tokenize

    Returns:
        List of lowercase tokens
    """
    if not text:
        return []
    tokens = re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", text.lower())
    return tokens


def _check_word_pair_for_regional_spelling(
    original_word: str, edited_word: str
) -> Optional[Dict[str, str]]:
    """Check if a word pair represents a regional spelling change.

    Args:
        original_word: The original word
        edited_word: The edited word

    Returns:
        Dictionary with change details if a regional spelling change is found, None otherwise
    """
    if original_word == edited_word:
        return None

    if (
        original_word in UK_TO_US_SPELLINGS
        and UK_TO_US_SPELLINGS[original_word] == edited_word
    ):
        return {
            "original_word": original_word,
            "edited_word": edited_word,
            "change_type": "UK_to_US",
        }
    elif (
        original_word in US_TO_UK_SPELLINGS
        and US_TO_UK_SPELLINGS[original_word] == edited_word
    ):
        return {
            "original_word": original_word,
            "edited_word": edited_word,
            "change_type": "US_to_UK",
        }

    return None


def find_regional_spelling_changes(
    original_text: str, edited_text: str
) -> List[Dict[str, str]]:
    """Identifies regional spelling changes between original and edited text.

    Args:
        original_text: The original text
        edited_text: The edited text

    Returns:
        List of dictionaries, each detailing a regional spelling change
    """
    original_tokens = _tokenize_for_spelling_check(original_text)
    edited_tokens = _tokenize_for_spelling_check(edited_text)
    changes = []

    diff = difflib.SequenceMatcher(None, original_tokens, edited_tokens)
    for tag, i1, i2, j1, j2 in diff.get_opcodes():
        if tag == "replace":
            original_segment = original_tokens[i1:i2]
            edited_segment = edited_tokens[j1:j2]

            if len(original_segment) == len(edited_segment):
                for original_word, edited_word in zip(
                    original_segment, edited_segment, strict=False
                ):
                    change = _check_word_pair_for_regional_spelling(
                        original_word, edited_word
                    )
                    if change:
                        changes.append(change)

    return changes
