"""Unit tests for the SpellingValidator."""

import pytest

from services.validation.validators.spelling_validator import SpellingValidator


@pytest.fixture
def spelling_validator():
    """Fixture for a SpellingValidator instance."""
    return SpellingValidator()


def test_correct_regional_spellings_no_change(spelling_validator):
    original = "This is a sentence with correct spelling."
    edited = "This is a sentence with correct spelling."
    result = spelling_validator.correct_regional_spellings(original, edited, 0, 1)
    assert result == edited


def test_correct_regional_spellings_with_correction(spelling_validator):
    original = "This is a sentence with recognise."
    edited = "This is a sentence with recognize."
    result = spelling_validator.correct_regional_spellings(original, edited, 0, 1)
    assert result == "This is a sentence with recognise."


def test_get_unique_corrections(spelling_validator):
    """Test _get_unique_corrections method with duplicates."""
    spelling_changes = [
        {"original_word": "colour", "edited_word": "color"},
        {"original_word": "colour", "edited_word": "color"},  # duplicate
        {"original_word": "favour", "edited_word": "favor"},
        {"original_word": "colour", "edited_word": "color"},  # another duplicate
    ]

    unique_corrections = spelling_validator._get_unique_corrections(spelling_changes)

    # Should have only 2 unique corrections
    assert len(unique_corrections) == 2

    # Check that both unique corrections are present
    expected_corrections = [
        {"original_word": "colour", "edited_word": "color"},
        {"original_word": "favour", "edited_word": "favor"},
    ]

    for expected in expected_corrections:
        assert expected in unique_corrections


def test_apply_spelling_corrections_case_preservation(spelling_validator):
    """Test _apply_spelling_corrections with various case scenarios."""
    text = "Color COLOR color Color"
    corrections = [{"original_word": "colour", "edited_word": "color"}]

    result, num_replacements = spelling_validator._apply_spelling_corrections(
        text, corrections
    )

    # All instances of "color" should be replaced with "colour" preserving case
    assert result == "Colour COLOUR colour Colour"
    assert num_replacements == 4


def test_preserve_case_all_caps(spelling_validator):
    """Test _preserve_case with all caps."""
    result = spelling_validator._preserve_case("colour", "COLOR")
    assert result == "COLOUR"


def test_preserve_case_all_lower(spelling_validator):
    """Test _preserve_case with all lowercase."""
    result = spelling_validator._preserve_case("colour", "color")
    assert result == "colour"


def test_preserve_case_title_case(spelling_validator):
    """Test _preserve_case with title case."""
    result = spelling_validator._preserve_case("colour", "Color")
    assert result == "Colour"


def test_preserve_case_mixed_case(spelling_validator):
    """Test _preserve_case with mixed case."""
    result = spelling_validator._preserve_case("colour", "CoLoR")
    assert result == "CoLoUr"


def test_preserve_case_different_lengths(spelling_validator):
    """Test _preserve_case when words have different lengths."""
    # Original longer than template
    result = spelling_validator._preserve_case("recognised", "RECOGN")
    assert result == "RECOGNISED"

    # Template longer than original (edge case)
    result = spelling_validator._preserve_case("color", "COLOURS")
    assert result == "COLOR"


def test_apply_spelling_corrections_no_matches(spelling_validator):
    """Test _apply_spelling_corrections when no matches are found."""
    text = "This text has no spelling variants."
    corrections = [{"original_word": "colour", "edited_word": "color"}]

    result, num_replacements = spelling_validator._apply_spelling_corrections(
        text, corrections
    )

    assert result == text  # Text should be unchanged
    assert num_replacements == 0


def test_apply_spelling_corrections_multiple_corrections(spelling_validator):
    """Test _apply_spelling_corrections with multiple different corrections."""
    text = "I recognize the color and favor this behavior."
    corrections = [
        {"original_word": "recognise", "edited_word": "recognize"},
        {"original_word": "colour", "edited_word": "color"},
        {"original_word": "favour", "edited_word": "favor"},
        {"original_word": "behaviour", "edited_word": "behavior"},
    ]

    result, num_replacements = spelling_validator._apply_spelling_corrections(
        text, corrections
    )

    expected = "I recognise the colour and favour this behaviour."
    assert result == expected
    assert num_replacements == 4


def test_correct_regional_spellings(spelling_validator):
    original = "This recognises the colour and favours this behaviour."
    edited = "This recognizes the color and favors this behavior."

    result = spelling_validator.correct_regional_spellings(original, edited, 2, 5)

    # Should correct back to original spellings
    expected = "This recognises the colour and favours this behaviour."
    assert result == expected
