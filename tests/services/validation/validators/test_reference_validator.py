"""Unit tests for the ReferenceValidator."""

from unittest.mock import MagicMock, patch

import pytest

from services.validation.validators.reference_validator import ReferenceValidator


@pytest.fixture
def reference_validator():
    """Fixture for a ReferenceValidator instance."""
    return ReferenceValidator()


def test_validate_references_no_change(reference_validator):
    original = 'This is a sentence with a <ref name="0" />.'
    edited = 'This is a sentence with a <ref name="0" />.'
    should_revert = reference_validator.validate_references(original, edited, 0, 1)
    assert not should_revert


def test_validate_references_revert_on_removal(reference_validator):
    original = 'This is a sentence with a <ref name="0" />.'
    edited = "This is a sentence."
    should_revert = reference_validator.validate_references(original, edited, 0, 1)
    assert should_revert


def test_validate_added_content_no_change(reference_validator):
    original = "This is a sentence."
    edited = "This is a sentence."
    should_revert = reference_validator.validate_added_content(original, edited, 0, 1)
    assert not should_revert


def test_validate_added_content_revert_on_new_link(reference_validator):
    original = "This is a sentence."
    edited = "This is a [[new link]] sentence."
    should_revert = reference_validator.validate_added_content(original, edited, 0, 1)
    assert should_revert


def test_validate_reference_content_changes_no_change(reference_validator):
    original = 'This is a sentence with a <ref name="ref1">content</ref>.'
    edited = 'This is a sentence with a <ref name="ref1">content</ref>.'
    should_revert = reference_validator.validate_reference_content_changes(
        original, edited, 0, 1
    )
    assert not should_revert


def test_validate_reference_content_changes_revert_on_change(reference_validator):
    original = 'This is a sentence with a <ref name="ref1">content</ref>.'
    edited = 'This is a sentence with a <ref name="ref1">different content</ref>.'
    should_revert = reference_validator.validate_reference_content_changes(
        original, edited, 0, 1
    )
    assert should_revert


def test_validate_added_content_exception_handling():
    """Test validate_added_content handles exceptions gracefully."""
    validator = ReferenceValidator()

    # Use patch to mock the method instead of direct assignment
    with patch.object(
        validator, "_check_added_references", side_effect=Exception("Test exception")
    ):
        result = validator.validate_added_content(
            "original content", "edited content", 0, 1
        )

    assert result is True  # Should return True on exception (revert)


def test_check_added_references_multiple_refs(reference_validator):
    """Test _check_added_references when new reference tags are added."""
    # Create mock parsed objects
    original_parsed = MagicMock()
    edited_parsed = MagicMock()

    # Original has 1 ref, edited has 2 refs
    original_parsed.get_tags.return_value = ["<ref>one</ref>"]
    edited_parsed.get_tags.return_value = ["<ref>one</ref>", "<ref>two</ref>"]

    should_revert = reference_validator._check_added_references(
        original_parsed, edited_parsed
    )

    assert should_revert


def test_create_ref_content_map_with_named_refs(reference_validator):
    """Test _create_ref_content_map with named references."""
    # Create mock ref tags
    ref1 = MagicMock()
    ref1.get_attr.return_value = "ref_name_1"
    ref1.contents = "Reference content 1"

    ref2 = MagicMock()
    ref2.get_attr.return_value = "ref_name_2"
    ref2.contents = "Reference content 2"

    ref_tags = [ref1, ref2]

    refs_map = reference_validator._create_ref_content_map(ref_tags)

    expected = {
        "ref_name_1": "Reference content 1",
        "ref_name_2": "Reference content 2",
    }

    assert refs_map == expected


def test_create_ref_content_map_without_names(reference_validator):
    """Test _create_ref_content_map with unnamed references."""
    # Create mock ref tags without names
    ref1 = MagicMock()
    ref1.get_attr.return_value = None  # No name attribute
    ref1.contents = "Reference content 1"
    ref1.configure_mock(**{"__str__.return_value": "<ref>Reference content 1</ref>"})

    ref2 = MagicMock()
    ref2.get_attr.return_value = None  # No name attribute
    ref2.contents = "Reference content 2"
    ref2.configure_mock(**{"__str__.return_value": "<ref>Reference content 2</ref>"})

    ref_tags = [ref1, ref2]

    refs_map = reference_validator._create_ref_content_map(ref_tags)

    expected = {
        "<ref>Reference content 1</ref>": "Reference content 1",
        "<ref>Reference content 2</ref>": "Reference content 2",
    }

    assert refs_map == expected


def test_check_reference_content_changes_missing_ref(reference_validator):
    """Test _check_reference_content_changes when a reference is missing."""
    original_refs_map = {"ref1": "content1", "ref2": "content2"}
    edited_refs_map = {"ref1": "content1"}  # ref2 is missing

    should_revert = reference_validator._check_reference_content_changes(
        original_refs_map, edited_refs_map
    )

    assert should_revert


def test_check_reference_content_changes_content_modified(reference_validator):
    """Test _check_reference_content_changes when reference content is modified."""
    original_refs_map = {"ref1": "original content", "ref2": "content2"}
    edited_refs_map = {"ref1": "modified content", "ref2": "content2"}

    should_revert = reference_validator._check_reference_content_changes(
        original_refs_map, edited_refs_map
    )

    assert should_revert


def test_validate_reference_content_changes_empty_refs_allowed(reference_validator):
    """Test that empty references being filled is allowed."""
    # Test with self-closing tag -> full tag (should be allowed)
    original = 'This has an empty ref <ref name="ref1" />.'
    edited = 'This has an empty ref <ref name="ref1">Now with content</ref>.'

    should_revert = reference_validator.validate_reference_content_changes(
        original, edited, 0, 1
    )

    assert not should_revert  # Should not revert - filling empty refs is allowed


def test_check_added_links_case_insensitive(reference_validator):
    """Test _check_added_links with case-insensitive comparison."""
    # Create mock parsed objects
    original_parsed = MagicMock()
    edited_parsed = MagicMock()

    # Original has link to "Example"
    original_link = MagicMock()
    original_link.target = "Example"
    original_parsed.wikilinks = [original_link]

    # Edited has links to "Example" and "example" (case variation) and "NewLink" (truly new)
    edited_link1 = MagicMock()
    edited_link1.target = "Example"
    edited_link2 = MagicMock()
    edited_link2.target = "example"  # Case variation
    edited_link3 = MagicMock()
    edited_link3.target = "NewLink"  # Truly new
    edited_parsed.wikilinks = [edited_link1, edited_link2, edited_link3]

    should_revert = reference_validator._check_added_links(
        original_parsed, edited_parsed
    )

    assert should_revert


def test_validate_added_content_with_prefix_added():
    """Test that adding a prefix doesn't cause links to be flagged as new."""
    validator = ReferenceValidator()

    original = "The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation."
    edited = "Edited: The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation."

    result = validator.validate_added_content(original, edited, 0, 1)

    # Should return False (no revert needed) because no new content was actually added
    assert result is False, (
        "Adding a prefix should not cause existing links to be flagged as new"
    )
