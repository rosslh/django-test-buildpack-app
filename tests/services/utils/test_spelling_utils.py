"""Tests for spelling utilities.

This module tests the SpellingUtils functionality.
"""

from services.utils.spelling_utils import (
    _check_word_pair_for_regional_spelling,
    find_regional_spelling_changes,
)


class TestSpellingUtils:
    """Test cases for SpellingUtils functions."""

    def test_tokenize_for_spelling_check_empty_string(self):
        """Test tokenization with empty string."""
        from services.utils.spelling_utils import _tokenize_for_spelling_check

        result = _tokenize_for_spelling_check("")
        assert result == []

    def test_tokenize_for_spelling_check_none(self):
        """Test tokenization with None input."""
        from services.utils.spelling_utils import _tokenize_for_spelling_check

        result = _tokenize_for_spelling_check(None)
        assert result == []

    def test_find_regional_spelling_changes_no_changes(self):
        """Test finding regional spelling changes when there are none."""
        original = "This is some text with color and flavor."
        edited = "This is some text with color and flavor."
        result = find_regional_spelling_changes(original, edited)
        assert result == []

    def test_find_regional_spelling_changes_unequal_segments(self):
        """Test finding regional spelling changes with unequal segments."""
        original = "The color was"
        edited = "The beautiful bright color was amazing"
        result = find_regional_spelling_changes(original, edited)
        assert result == []  # Should be empty because segments are unequal

    def test_find_regional_spelling_changes_no_match_in_dict(self):
        """Test finding regional spelling changes with words not in dictionary."""
        original = "random word"
        edited = "different word"
        result = find_regional_spelling_changes(original, edited)
        assert result == []

    def test_find_regional_spelling_changes_with_real_changes(self):
        """Test finding actual regional spelling changes."""
        original = "The color and flavor were great."
        edited = "The colour and flavour were great."
        result = find_regional_spelling_changes(original, edited)
        assert len(result) == 2
        assert any(
            change["original_word"] == "color" and change["edited_word"] == "colour"
            for change in result
        )
        assert any(
            change["original_word"] == "flavor" and change["edited_word"] == "flavour"
            for change in result
        )

    def test_check_word_pair_for_regional_spelling_same_words(self):
        """Test checking word pairs when words are the same."""
        result = _check_word_pair_for_regional_spelling("color", "color")
        assert result is None

    def test_check_word_pair_for_regional_spelling_different_non_variants(self):
        """Test checking word pairs when words are different but not regional
        variants."""
        result = _check_word_pair_for_regional_spelling("apple", "banana")
        assert result is None

    def test_check_word_pair_for_regional_spelling_uk_to_us(self):
        """Test checking word pairs for UK to US spelling changes."""
        result = _check_word_pair_for_regional_spelling("colour", "color")
        expected = {
            "original_word": "colour",
            "edited_word": "color",
            "change_type": "UK_to_US",
        }
        assert result == expected

    def test_check_word_pair_for_regional_spelling_us_to_uk(self):
        """Test checking word pairs for US to UK spelling changes."""
        result = _check_word_pair_for_regional_spelling("color", "colour")
        expected = {
            "original_word": "color",
            "edited_word": "colour",
            "change_type": "US_to_UK",
        }
        assert result == expected
