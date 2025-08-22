"""Unit tests for the MetaCommentaryValidator."""

from typing import Any, Dict

import pytest

from services.core.interfaces import IValidator
from services.validation.validators.meta_commentary_validator import (
    MetaCommentaryValidator,
)


@pytest.fixture
def validator():
    """Fixture for a MetaCommentaryValidator instance."""
    return MetaCommentaryValidator()


def test_validator_implements_interface(validator):
    """Test that MetaCommentaryValidator implements IValidator interface."""
    assert isinstance(validator, IValidator)


def test_no_meta_commentary_in_original_or_edited():
    """Test when neither original nor edited text contains meta commentary."""
    validator = MetaCommentaryValidator()
    original = "The quick brown fox jumps over the lazy dog."
    edited = "The fast brown fox leaps over the lazy dog."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == edited
    assert should_revert is False
    assert validator.get_last_failure_reason() is None


def test_meta_commentary_allowed_when_in_original():
    """Test that meta commentary is allowed when it exists in the original text."""
    validator = MetaCommentaryValidator()
    original = "I think this article needs some edits to improve the wikitext."
    edited = "I believe this article needs some edits to improve the wikitext."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == edited
    assert should_revert is False
    assert validator.get_last_failure_reason() is None


def test_rejects_edit_with_meta_commentary_word_i():
    """Test that edits containing 'I' are rejected when not in original."""
    validator = MetaCommentaryValidator()
    original = "The cat sat on the mat."
    edited = "I could not identify any changes needed for this text."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()
    assert "'I'" in failure_reason


def test_rejects_edit_with_meta_commentary_word_me():
    """Test that edits containing 'me' are rejected when not in original."""
    validator = MetaCommentaryValidator()
    original = "The weather is nice today."
    edited = "Let me help you improve this sentence."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()
    assert "'me'" in failure_reason


def test_rejects_edit_with_meta_commentary_word_edit():
    """Test that edits containing 'edit' are rejected when not in original."""
    validator = MetaCommentaryValidator()
    original = "This is a simple sentence."
    edited = "This edit improves the sentence structure."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()
    assert "'edit'" in failure_reason


def test_rejects_edit_with_meta_commentary_word_please():
    """Test that edits containing 'please' are rejected when not in original."""
    validator = MetaCommentaryValidator()
    original = "The sun is shining."
    edited = "Please review this improved sentence."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()
    assert "'Please'" in failure_reason


def test_rejects_edit_with_meta_commentary_word_wikitext():
    """Test that edits containing 'wikitext' are rejected when not in original."""
    validator = MetaCommentaryValidator()
    original = "This is an encyclopedia article."
    edited = "I cannot find any wikitext formatting issues."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()
    assert "'wikitext'" in failure_reason


def test_case_insensitive_detection():
    """Test that meta commentary detection is case insensitive."""
    validator = MetaCommentaryValidator()
    original = "The book is interesting."
    edited = "I cannot EDIT this text properly."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()


def test_word_boundary_detection():
    """Test that only whole words are detected, not partial matches."""
    validator = MetaCommentaryValidator()
    original = "The medicine was effective."
    edited = "The medication was effective."  # 'me' is part of 'medicine/medication', should not trigger
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == edited
    assert should_revert is False
    assert validator.get_last_failure_reason() is None


def test_multiple_meta_commentary_words():
    """Test detection when multiple meta commentary words are present."""
    validator = MetaCommentaryValidator()
    original = "The dog barked loudly."
    edited = "I think you should please edit this wikitext."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "meta commentary" in failure_reason.lower()
    # Should mention at least one of the detected words
    assert any(
        word in failure_reason for word in ["'I'", "'please'", "'edit'", "'wikitext'"]
    )


def test_meta_commentary_in_middle_of_sentence():
    """Test detection when meta commentary words appear in the middle of sentences."""
    validator = MetaCommentaryValidator()
    original = "The car drove down the street."
    edited = "The car, which I noticed yesterday, drove down the street."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "'I'" in failure_reason


def test_substring_not_detected_comprehensive():
    """Test that forbidden words as substrings don't trigger the validator."""
    validator = MetaCommentaryValidator()

    # Test various words containing forbidden substrings
    test_cases = [
        (
            "The research was thorough.",
            "We should investigate this claim thoroughly.",
        ),  # "I" in "investigate"
        (
            "The building is old.",
            "The edited volume contains many articles.",
        ),  # "edit" in "edited"
        (
            "The system works.",
            "They welcomed the new members warmly.",
        ),  # "me" in "welcomed"
        (
            "The text is long.",
            "The context of the statement matters.",
        ),  # "text" in "context"
        (
            "The book is good.",
            "We completed the implementation successfully.",
        ),  # "I" in "implementation"
    ]

    for original, edited in test_cases:
        context: Dict[str, Any] = {}
        result, should_revert = validator.validate(original, edited, context)

        assert result == edited, f"Should not revert: '{original}' -> '{edited}'"
        assert should_revert is False, f"Should not revert: '{original}' -> '{edited}'"
        assert validator.get_last_failure_reason() is None, (
            f"Should not fail: '{original}' -> '{edited}'"
        )


def test_case_changes_allowed_when_word_in_original():
    """Test that case changes are allowed when the word exists in original text."""
    validator = MetaCommentaryValidator()

    # Test cases where meta commentary words exist in original with different casing
    test_cases = [
        (
            "please review this draft",
            "Please review this draft carefully",
        ),  # "please" -> "Please"
        ("I think this works", "i believe this works well"),  # "I" -> "i"
        ("The edit was good", "The EDIT was excellent"),  # "edit" -> "EDIT"
        (
            "wikitext formatting",
            "Wikitext formatting is important",
        ),  # "wikitext" -> "Wikitext"
        ("Let me explain", "Let ME clarify this point"),  # "me" -> "ME"
    ]

    for original, edited in test_cases:
        context: Dict[str, Any] = {}
        result, should_revert = validator.validate(original, edited, context)

        assert result == edited, f"Should allow case change: '{original}' -> '{edited}'"
        assert should_revert is False, (
            f"Should allow case change: '{original}' -> '{edited}'"
        )
        assert validator.get_last_failure_reason() is None, (
            f"Should allow case change: '{original}' -> '{edited}'"
        )


def test_mixed_allowed_and_forbidden_words():
    """Test scenarios with both allowed and forbidden meta commentary words."""
    validator = MetaCommentaryValidator()

    # Original has "edit" but edited adds "I" - should reject because of "I"
    original = "This edit improves the text."
    edited = "I think this edit improves the text significantly."
    context: Dict[str, Any] = {}

    result, should_revert = validator.validate(original, edited, context)

    assert result == original
    assert should_revert is True
    failure_reason = validator.get_last_failure_reason()
    assert failure_reason is not None
    assert "'I'" in failure_reason
    # Should not mention "edit" since it's allowed
    assert "'edit'" not in failure_reason.lower() or "'Edit'" not in failure_reason


def test_complex_substring_scenarios():
    """Test more complex substring scenarios to ensure robustness."""
    validator = MetaCommentaryValidator()

    # Test cases with multiple potential substring matches
    test_cases = [
        (
            "The document is complete.",
            "Investigate the editing process carefully.",
        ),  # "I" in investigate, "edit" in editing
        (
            "Research shows success.",
            "We pleased the editorial team.",
        ),  # "please" in pleased, "edit" in editorial
        (
            "The work continues.",
            "Implementation requires careful consideration.",
        ),  # "I" in implementation, "me" in implementation
        (
            "Analysis is done.",
            "Wikipedia's editing guidelines are helpful.",
        ),  # "I" in Wikipedia, "edit" in editing
    ]

    for original, edited in test_cases:
        context: Dict[str, Any] = {}
        result, should_revert = validator.validate(original, edited, context)

        assert result == edited, (
            f"Should not revert complex substring case: '{original}' -> '{edited}'"
        )
        assert should_revert is False, (
            f"Should not revert complex substring case: '{original}' -> '{edited}'"
        )
        assert validator.get_last_failure_reason() is None, (
            f"Should not fail complex substring case: '{original}' -> '{edited}'"
        )


def test_new_meta_commentary_words():
    """Test the new meta commentary words added to the constants."""
    validator = MetaCommentaryValidator()

    # Test cases for the remaining new words (removed cannot, unable, suggest, recommend)
    test_cases = [
        ("The content is fine.", "Sorry, but I cannot help with this."),  # "sorry"
        ("The writing is clear.", "I apologize but cannot edit this."),  # "apologize"
    ]

    for original, edited in test_cases:
        context: Dict[str, Any] = {}
        result, should_revert = validator.validate(original, edited, context)

        assert result == original, (
            f"Should revert meta commentary: '{original}' -> '{edited}'"
        )
        assert should_revert is True, (
            f"Should revert meta commentary: '{original}' -> '{edited}'"
        )
        failure_reason = validator.get_last_failure_reason()
        assert failure_reason is not None, (
            f"Should have failure reason: '{original}' -> '{edited}'"
        )
        assert "meta commentary" in failure_reason.lower()


def test_new_words_allowed_when_in_original():
    """Test that new meta commentary words are allowed when they exist in original text."""
    validator = MetaCommentaryValidator()

    # Test cases where remaining new meta commentary words exist in original
    test_cases = [
        (
            "Sorry for the confusion.",
            "Sorry about the delay in response.",
        ),  # "sorry" in both
        (
            "I apologize for the error.",
            "We apologize for any inconvenience.",
        ),  # "apologize" in both
    ]

    for original, edited in test_cases:
        context: Dict[str, Any] = {}
        result, should_revert = validator.validate(original, edited, context)

        assert result == edited, (
            f"Should allow when word in original: '{original}' -> '{edited}'"
        )
        assert should_revert is False, (
            f"Should allow when word in original: '{original}' -> '{edited}'"
        )
        assert validator.get_last_failure_reason() is None, (
            f"Should not fail when word in original: '{original}' -> '{edited}'"
        )


def test_substring_protection_for_new_words():
    """Test that substrings of new meta commentary words don't trigger false positives."""
    validator = MetaCommentaryValidator()

    # Test cases where remaining new words appear as substrings
    test_cases = [
        (
            "The team works hard.",
            "They felt sorry for the mistake.",
        ),  # "sorry" as whole word should trigger
        (
            "Progress continues.",
            "The laboratory equipment malfunctioned.",
        ),  # "apolog" in laboratory should not trigger "apologize"
    ]

    # Test that whole words trigger but substrings don't
    original, edited = test_cases[0]  # "sorry" as whole word
    context: Dict[str, Any] = {}
    result, should_revert = validator.validate(original, edited, context)
    assert should_revert is True, "Should detect 'sorry' as whole word"

    original, edited = test_cases[1]  # "apolog" in "laboratory"
    result, should_revert = validator.validate(original, edited, context)
    assert should_revert is False, "Should not detect 'apologize' in 'laboratory'"
