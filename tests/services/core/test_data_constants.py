"""Test cases for data constants module."""

from services.core.data_constants import (
    ALL_SPELLING_VARIANTS,
    UK_TO_US_SPELLINGS,
    US_TO_UK_SPELLINGS,
)


def test_spelling_variants_structure():
    """Test the structure of spelling variant dictionaries."""
    assert isinstance(UK_TO_US_SPELLINGS, dict)
    assert isinstance(US_TO_UK_SPELLINGS, dict)
    assert isinstance(ALL_SPELLING_VARIANTS, dict)


def test_spelling_variants_basic_mappings():
    """Test basic spelling variant mappings."""
    # Test some basic UK to US mappings
    assert "colour" in UK_TO_US_SPELLINGS
    assert UK_TO_US_SPELLINGS["colour"] == "color"
    assert "analyse" in UK_TO_US_SPELLINGS
    assert UK_TO_US_SPELLINGS["analyse"] == "analyze"

    # Test reverse mappings
    assert "color" in US_TO_UK_SPELLINGS
    assert US_TO_UK_SPELLINGS["color"] == "colour"
    assert "analyze" in US_TO_UK_SPELLINGS
    assert US_TO_UK_SPELLINGS["analyze"] == "analyse"


def test_all_spelling_variants():
    """Test that ALL_SPELLING_VARIANTS contains both directions."""
    assert "colour" in ALL_SPELLING_VARIANTS
    assert "color" in ALL_SPELLING_VARIANTS
    assert "analyse" in ALL_SPELLING_VARIANTS
    assert "analyze" in ALL_SPELLING_VARIANTS


def test_spelling_variants_consistency():
    """Test consistency between the dictionaries."""
    # ALL_SPELLING_VARIANTS should contain all entries from both dictionaries
    for word in UK_TO_US_SPELLINGS:
        assert word in ALL_SPELLING_VARIANTS
    for word in US_TO_UK_SPELLINGS:
        assert word in ALL_SPELLING_VARIANTS

    # Check that US_TO_UK_SPELLINGS is properly the reverse of UK_TO_US_SPELLINGS
    for uk_word, us_word in UK_TO_US_SPELLINGS.items():
        assert us_word in US_TO_UK_SPELLINGS
        assert US_TO_UK_SPELLINGS[us_word] == uk_word


def test_spelling_variants_non_empty():
    """Test that the dictionaries are not empty."""
    assert len(UK_TO_US_SPELLINGS) > 0
    assert len(US_TO_UK_SPELLINGS) > 0
    assert len(ALL_SPELLING_VARIANTS) > 0
    # ALL_SPELLING_VARIANTS combines both dictionaries
    assert len(ALL_SPELLING_VARIANTS) >= len(UK_TO_US_SPELLINGS)
    assert len(ALL_SPELLING_VARIANTS) >= len(US_TO_UK_SPELLINGS)
