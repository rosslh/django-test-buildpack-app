"""Tests for reference handler.

This module tests the ReferenceHandler functionality.
"""

from services.text.reference_handler import ReferenceHandler


class TestReferenceHandler:
    """Test cases for ReferenceHandler class."""

    def test_restore_references_simple_placeholder_fallback(self):
        """Test that simple placeholders are no longer supported."""
        handler = ReferenceHandler()

        # Test case where only simple placeholder is present - it should NOT be replaced
        text_with_placeholders = "This is a test with reference 0 in it."
        references = ["<ref>Test Reference</ref>"]

        result = handler.restore_references(text_with_placeholders, references)
        # Simple placeholders are no longer supported, so text should remain unchanged
        expected = "This is a test with reference 0 in it."

        assert result == expected

    def test_restore_references_mixed_formats(self):
        """Test restore_references with XML placeholders only."""
        handler = ReferenceHandler()

        # Only XML format placeholders should be replaced
        text_with_placeholders = 'Text with <ref name="0" /> and also 1 here.'
        references = ["<ref>First Reference</ref>", "<ref>Second Reference</ref>"]

        result = handler.restore_references(text_with_placeholders, references)
        # Only the XML placeholder should be replaced, simple "1" should remain
        expected = "Text with <ref>First Reference</ref> and also 1 here."

        assert result == expected

    def test_replace_references_with_placeholders(self):
        """Test replacing references with placeholders."""
        handler = ReferenceHandler()
        text = "Text with <ref>reference</ref> content."

        result_text, refs = handler.replace_references_with_placeholders(text)

        assert result_text == 'Text with <ref name="0" /> content.'
        assert refs == ["<ref>reference</ref>"]

    def test_restore_references(self):
        """Test restoring references from placeholders."""
        handler = ReferenceHandler()
        text_with_placeholders = 'Text with <ref name="0" /> content.'
        references = ["<ref>reference</ref>"]

        result = handler.restore_references(text_with_placeholders, references)

        assert result == "Text with <ref>reference</ref> content."

    def test_restore_references_no_simple_placeholder_matching(self):
        """Test that digits in content are never replaced (simple placeholders removed)."""
        handler = ReferenceHandler()

        # This tests that digits in content are never replaced since simple placeholders are removed
        text_with_placeholders = "The date was 2013 and reference 0 was cited."
        references = ["<ref>Important source from 2013</ref>"]

        result = handler.restore_references(text_with_placeholders, references)

        # No replacement should happen since only XML format placeholders are supported
        expected = "The date was 2013 and reference 0 was cited."

        assert result == expected, "Simple placeholders should not be supported"
        assert "2013" in result, "The original date should remain intact"

    def test_restore_references_with_xml_placeholders_only(self):
        """Test that only XML format placeholders work correctly."""
        handler = ReferenceHandler()

        # Simulate content with XML placeholders
        original_content = 'The FreeBSD project stated "it is very favorable" in 2013.<ref>{{cite web|date=13 November 2013 |access-date=28 November 2015}}</ref>'

        # Replace with placeholders
        text_with_placeholders, refs_list = (
            handler.replace_references_with_placeholders(original_content)
        )

        # Make a simple edit (remove "very")
        edited_with_placeholders = text_with_placeholders.replace(
            "very favorable", "favorable"
        )

        # Restore references - should work correctly with XML placeholders
        restored = handler.restore_references(edited_with_placeholders, refs_list)

        # Should work correctly now that simple placeholders are removed
        expected_correct = 'The FreeBSD project stated "it is favorable" in 2013.<ref>{{cite web|date=13 November 2013 |access-date=28 November 2015}}</ref>'

        assert restored == expected_correct, "XML placeholders should work correctly"
        assert "2013" in restored, "Original dates should remain intact"
