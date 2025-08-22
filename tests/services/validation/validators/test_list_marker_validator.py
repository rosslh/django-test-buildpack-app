"""Unit tests for the ListMarkerValidator."""

import pytest

from services.validation.validators.list_marker_validator import ListMarkerValidator


@pytest.fixture
def list_marker_validator():
    """Fixture for a ListMarkerValidator instance."""
    return ListMarkerValidator()


def test_validate_and_restore_list_markers_no_change(list_marker_validator):
    original = "* This is a list item."
    edited = "* This is a list item."
    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 0, 1
    )
    assert result == edited


def test_validate_and_restore_list_markers_with_change(list_marker_validator):
    original = "* This is a list item."
    edited = "# This is a list item."
    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 0, 1
    )
    assert result == "* This is a list item."


def test_validate_and_restore_list_markers_not_list_item(list_marker_validator):
    """Test with content that's not a list item."""
    original = "This is regular text."
    edited = "This is edited regular text."
    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 0, 1
    )
    assert result == edited


def test_validate_and_restore_list_markers_spacing_change(list_marker_validator):
    """Test when spacing after marker is changed."""
    original = "*   This is a list item with specific spacing."
    edited = "* This is a list item with different spacing."
    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 0, 1
    )
    assert result == "*   This is a list item with different spacing."


def test_validate_and_restore_list_markers_marker_removed(list_marker_validator):
    """Test when marker is completely removed."""
    original = "* This is a list item."
    edited = "This is no longer a list item."
    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 0, 1
    )
    # Should restore the spacing since marker was removed - with space after marker
    assert result == "* This is no longer a list item."


def test_restore_list_marker_fallback_to_original(list_marker_validator):
    """Test _restore_list_marker fallback when regex matching fails."""
    original = "* Original content."
    # Create malformed edited text that won't match the pattern
    edited = "malformed_content_without_proper_marker"

    result = list_marker_validator._restore_list_marker(original, edited, "*", "#")

    assert result == original


def test_extract_list_marker_various_types(list_marker_validator):
    """Test _extract_list_marker with various marker types."""
    assert list_marker_validator._extract_list_marker("* item") == "*"
    assert list_marker_validator._extract_list_marker("** nested item") == "**"
    assert list_marker_validator._extract_list_marker("# numbered item") == "#"
    assert list_marker_validator._extract_list_marker("## nested numbered") == "##"
    assert list_marker_validator._extract_list_marker("; definition") == ";"
    assert list_marker_validator._extract_list_marker("  * spaced item") == "*"
    assert list_marker_validator._extract_list_marker("regular text") is None


def test_extract_marker_with_spacing_various_cases(list_marker_validator):
    """Test _extract_marker_with_spacing with various spacing scenarios."""
    assert list_marker_validator._extract_marker_with_spacing("* ") == "* "
    assert list_marker_validator._extract_marker_with_spacing("*  ") == "*  "
    assert list_marker_validator._extract_marker_with_spacing("*") == "*"
    assert list_marker_validator._extract_marker_with_spacing("**   ") == "**   "
    assert list_marker_validator._extract_marker_with_spacing("#\t") == "#\t"
    assert list_marker_validator._extract_marker_with_spacing("regular text") is None


def test_restore_list_marker_with_complex_spacing(list_marker_validator):
    """Test _restore_list_marker preserves original spacing pattern."""
    original = "**   Original content with complex spacing."
    edited = "#  New content."

    result = list_marker_validator._restore_list_marker(original, edited, "**", "#")

    assert result == "**   New content."


def test_validate_and_restore_complex_marker_change(list_marker_validator):
    """Test full workflow with complex marker changes."""
    original = "*** Deep nested item with content."
    edited = "# Changed to numbered list."

    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 2, 5
    )

    # The validator preserves spacing, so expect space after marker
    assert result == "*** Changed to numbered list."


def test_validate_and_restore_marker_added_with_spacing(list_marker_validator):
    """Test when a list marker is added to non-list text with spacing."""
    original = "This is regular paragraph text."
    edited = "*   This is now a list item with spacing."

    result = list_marker_validator.validate_and_restore_list_markers(
        original, edited, 0, 1
    )

    # Should remove the added list marker and its spacing
    assert result == "This is now a list item with spacing."
