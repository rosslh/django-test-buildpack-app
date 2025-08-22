"""Tests for the ContentClassifier module.

This module tests the ContentClassifier functionality to ensure proper classification of
content for processing decisions.
"""

from services.document.classifier import ContentClassifier


class TestContentClassifier:
    """Test cases for ContentClassifier class."""

    def test_should_skip_item_empty_content(self):
        """Test that empty content is skipped."""
        assert ContentClassifier.should_skip_item("")
        assert ContentClassifier.should_skip_item("   ")
        assert ContentClassifier.should_skip_item("\n\t")

    def test_should_skip_item_code_blocks(self):
        """Test that code blocks are skipped."""
        assert ContentClassifier.should_skip_item("```python\nprint('hello')\n```")
        assert ContentClassifier.should_skip_item("```\nsome code\n```")
        assert ContentClassifier.should_skip_item("```json")

    def test_should_skip_item_non_prose_prefixes(self):
        """Test that content with non-prose prefixes is skipped."""
        # Test various markers from NON_PROSE_PREFIXES
        assert ContentClassifier.should_skip_item("==Header==")
        assert ContentClassifier.should_skip_item("* Bullet point")
        assert ContentClassifier.should_skip_item("# Numbered list")
        assert ContentClassifier.should_skip_item("{{Template}}")
        assert ContentClassifier.should_skip_item("[[Category:Example]]")
        assert ContentClassifier.should_skip_item("[[File:example.jpg]]")
        assert ContentClassifier.should_skip_item("| Table row")
        assert ContentClassifier.should_skip_item("> Blockquote")

    def test_should_skip_item_categories_anywhere(self):
        """Test that content containing categories anywhere is skipped."""
        # Regular categories
        assert ContentClassifier.should_skip_item(
            "This is a paragraph that contains [[Category:United States]] somewhere in the middle."
        )
        assert ContentClassifier.should_skip_item(
            "Multiple categories: [[Category:Countries]] and [[Category:History]] present."
        )

        # Visible category links
        assert ContentClassifier.should_skip_item(
            "For more information, see [[:Category:American politics]] page."
        )

        # Case insensitive
        assert ContentClassifier.should_skip_item(
            "This has [[category:lowercase]] category."
        )
        assert ContentClassifier.should_skip_item(
            "This has [[CATEGORY:UPPERCASE]] category."
        )

        # Complex category names
        assert ContentClassifier.should_skip_item(
            "Article contains [[Category:21st-century American politicians]] category."
        )

    def test_should_skip_item_short_content(self):
        """Test that short content is skipped."""
        # Content shorter than MIN_PARAGRAPH_LENGTH
        assert ContentClassifier.should_skip_item("Short text")
        assert ContentClassifier.should_skip_item("Only a few words here")

    def test_should_skip_item_unclosed_tags(self):
        """Test that content with unclosed tags is skipped."""
        # Unclosed ref tags
        assert ContentClassifier.should_skip_item(
            "This paragraph has an unclosed <ref>citation that contains a newline\nand continues here"
        )
        assert ContentClassifier.should_skip_item(
            "Multiple unclosed tags <ref>first citation and <nowiki>some nowiki content that is not closed properly in this long paragraph"
        )

        # Unclosed nowiki tags
        assert ContentClassifier.should_skip_item(
            "This paragraph contains <nowiki>some text that should not be processed\nbut the tag is never closed in this sufficiently long paragraph"
        )

        # Unclosed comment tags
        assert ContentClassifier.should_skip_item(
            "This paragraph has an unclosed <!-- HTML comment that spans multiple lines\nand should cause the paragraph to be skipped because it's malformed wikitext"
        )

        # Orphaned closing tags (closing without opening)
        assert ContentClassifier.should_skip_item(
            "This paragraph has an orphaned closing </ref> tag without a corresponding opening tag in this long paragraph"
        )
        assert ContentClassifier.should_skip_item(
            "This paragraph contains an orphaned </nowiki> closing tag that should cause it to be skipped from processing"
        )
        assert ContentClassifier.should_skip_item(
            "This paragraph has an orphaned --> comment closing tag without an opening comment in this long paragraph"
        )

    def test_should_skip_item_invalid_wikitext_markup(self):
        """Test that content with invalid wikitext markup is skipped."""
        # Unmatched brackets
        assert ContentClassifier.should_skip_item(
            "This paragraph has unmatched [[wikilink brackets that are not properly closed in this long paragraph"
        )
        assert ContentClassifier.should_skip_item(
            "This paragraph has unmatched {{template brackets that are not properly closed in this long paragraph"
        )

        # Orphaned closing brackets (closing without opening)
        assert ContentClassifier.should_skip_item(
            "This paragraph has orphaned ]] closing wikilink brackets without corresponding opening brackets in this long paragraph"
        )
        assert ContentClassifier.should_skip_item(
            "This paragraph contains orphaned }} closing template brackets that should cause it to be skipped from processing"
        )

        # Mixed unclosed tags
        assert ContentClassifier.should_skip_item(
            "Complex case with <ref>unclosed ref and [[unclosed wikilink and {{unclosed template in this long paragraph"
        )

        # Mixed orphaned closing tags
        assert ContentClassifier.should_skip_item(
            "Complex case with orphaned </ref> and ]] and }} closing tags without corresponding opening tags in this long paragraph"
        )

    def test_should_skip_item_valid_content(self):
        """Test that valid prose content is not skipped."""
        valid_prose = "This is a sufficiently long paragraph that contains regular prose content and should not be skipped by the classifier."
        assert not ContentClassifier.should_skip_item(valid_prose)

    def test_should_skip_item_valid_content_with_wikilinks(self):
        """Test that valid prose with regular wikilinks is not skipped."""
        valid_prose_with_links = "This is a sufficiently long paragraph that contains regular [[wikilinks]] and [[Article|display text]] but no categories, so it should not be skipped."
        assert not ContentClassifier.should_skip_item(valid_prose_with_links)

    def test_should_skip_item_valid_content_with_closed_tags(self):
        """Test that valid prose with properly closed tags is not skipped."""
        # Properly closed ref tags
        valid_with_refs = "This is a sufficiently long paragraph with properly closed <ref>citation content</ref> that should be processed normally."
        assert not ContentClassifier.should_skip_item(valid_with_refs)

        # Properly closed nowiki tags
        valid_with_nowiki = "This paragraph contains <nowiki>some text that should not be processed</nowiki> but the tags are properly closed so it should be processed."
        assert not ContentClassifier.should_skip_item(valid_with_nowiki)

        # Properly closed comments
        valid_with_comments = "This paragraph has a <!-- properly closed comment --> and should be processed normally as it contains sufficient content."
        assert not ContentClassifier.should_skip_item(valid_with_comments)

    def test_should_skip_item_edge_cases(self):
        """Test edge cases for should_skip_item."""
        # Content at the boundary length
        boundary_content = "A" * 47  # Just under MIN_PARAGRAPH_LENGTH (48)
        assert ContentClassifier.should_skip_item(boundary_content)

        sufficient_content = "A" * 48  # At MIN_PARAGRAPH_LENGTH
        assert not ContentClassifier.should_skip_item(sufficient_content)

    # Test from test_processing.py
    def test_content_classifier_is_processable_prose(self):
        classifier = ContentClassifier()

        # Test with prose content
        assert classifier.is_processable_prose(
            "This is a normal paragraph that is long enough to be processed."
        )

        # Test with non-prose content
        assert not classifier.is_processable_prose("* This is a bullet point.")
        assert not classifier.is_processable_prose("# This is a numbered list.")
        assert not classifier.is_processable_prose("{{Template:Example}}")
        assert not classifier.is_processable_prose("| This is a table row.")
        assert not classifier.is_processable_prose("==")
        assert not classifier.is_processable_prose("This is too short")

    def test_is_processable_prose_with_categories(self):
        """Test that prose with categories is not considered processable."""
        classifier = ContentClassifier()

        # Even if it's long enough and otherwise prose-like, categories should make it non-processable
        prose_with_category = "This is a sufficiently long paragraph that would normally be processed, but it contains [[Category:United States]] which should make it non-processable."
        assert not classifier.is_processable_prose(prose_with_category)

        prose_with_visible_category = "This is another long paragraph that mentions [[:Category:History]] as a visible link, so it should not be processed."
        assert not classifier.is_processable_prose(prose_with_visible_category)

    def test_should_skip_item_wikitextparser_exception(self):
        """Test that content causing wikitextparser exceptions is skipped."""
        # Using a patch to force wikitextparser to raise an exception
        from unittest.mock import patch

        with patch(
            "services.document.classifier.wtp.parse",
            side_effect=Exception("Parse error"),
        ):
            invalid_content = "This is a sufficiently long paragraph that causes wikitextparser to fail and should be skipped."
            assert ContentClassifier.should_skip_item(invalid_content)

    def test_refactored_classifier_maintains_business_logic(self):
        """Test that the refactored classifier maintains the correct business logic."""
        classifier = ContentClassifier()

        # Test document: first prose should be skipped, second prose should be processed
        document_items = [
            "First prose paragraph that should be skipped even though it's valid prose content and long enough to normally be processed.",
            "Second prose paragraph that should be processed because it's the second prose after skipping the first one.",
            "==See also==",
            "Prose in footer section should be skipped even though it would normally be processable prose content.",
        ]

        # Test with context - first prose should be skipped
        should_process_0, skip_reason_0 = classifier.should_process_with_context(
            document_items[0], 0, document_items
        )
        assert not should_process_0, "First prose paragraph should be skipped"
        assert (
            skip_reason_0
            == "First prose paragraph in lead section - skipped to preserve article structure"
        )

        # Second prose should be processed
        should_process_1, skip_reason_1 = classifier.should_process_with_context(
            document_items[1], 1, document_items
        )
        assert should_process_1, "Second prose paragraph should be processed"
        assert skip_reason_1 is None

        # Footer section heading should be skipped
        should_process_2, skip_reason_2 = classifier.should_process_with_context(
            document_items[2], 2, document_items
        )
        assert not should_process_2, "Footer section heading should be skipped"
        assert skip_reason_2 == "Footer heading"

        # Content in footer section should be skipped
        should_process_3, skip_reason_3 = classifier.should_process_with_context(
            document_items[3], 3, document_items
        )
        assert not should_process_3, "Content in footer section should be skipped"
        assert (
            skip_reason_3
            == "Prose content in footer section - skipped per editorial guidelines"
        )

        # Verify state tracking
        assert classifier.has_first_prose_been_encountered(), (
            "First prose should have been encountered"
        )
        assert classifier.is_in_footer_section(), "Should be in footer section"

        # Test content types
        assert classifier.get_content_type(document_items[0]) == "prose"
        assert classifier.get_content_type(document_items[1]) == "prose"
        assert classifier.get_content_type(document_items[2]) == "footer-heading"
        assert (
            classifier.get_content_type(document_items[3]) == "prose"
        )  # Still prose, but skipped due to footer context

        # Test is_processable_prose method (should work with new implementation)
        assert classifier.is_processable_prose(document_items[0])
        assert classifier.is_processable_prose(document_items[1])
        assert not classifier.is_processable_prose(
            document_items[2]
        )  # footer heading is not prose
        assert classifier.is_processable_prose(
            document_items[3]
        )  # still prose, context matters for processing decision

    def test_footer_section_processing_with_multiple_items(self):
        """Test processing behavior when multiple items are in footer section."""
        classifier = ContentClassifier()

        # Create a document with multiple footer items to ensure we hit the footer return False branch
        document_items = [
            "This is the first prose paragraph that should be skipped.",
            "This is the second prose paragraph that should be processed.",
            "==References==",  # This triggers footer section
            "This prose content is in footer section and should be skipped.",
            "This is another prose content in footer section that should also be skipped.",
        ]

        # Process items in sequence to build state
        should_process_0, _ = classifier.should_process_with_context(
            document_items[0], 0, document_items
        )  # Skip first prose
        assert not should_process_0
        should_process_1, _ = classifier.should_process_with_context(
            document_items[1], 1, document_items
        )  # Process second prose
        assert should_process_1
        should_process_2, _ = classifier.should_process_with_context(
            document_items[2], 2, document_items
        )  # Skip footer heading
        assert not should_process_2

        should_process_3, _ = classifier.should_process_with_context(
            document_items[3], 3, document_items
        )  # Skip footer prose
        assert not should_process_3
        should_process_4, _ = classifier.should_process_with_context(
            document_items[4], 4, document_items
        )  # Skip another footer prose
        assert not should_process_4

        # Verify we're in footer section
        assert classifier.is_in_footer_section()

    def test_should_process_with_context_non_processable_prose(self):
        """Test that non-processable prose is correctly handled in should_process_with_context."""
        classifier = ContentClassifier()

        # Test with non-processable content (too short, templates, etc.)
        document_items = [
            "This is the first prose paragraph that should be skipped.",
            "Short",  # Too short - should hit the non-processable prose return False
            "{{Template:Example that is sufficiently long to pass length check}}",  # Template - should hit non-processable return False
        ]

        # Process first item to get past the first prose skip
        should_process_0, _ = classifier.should_process_with_context(
            document_items[0], 0, document_items
        )
        assert not should_process_0

        # These should hit the non-processable prose return False branch
        should_process_1, _ = classifier.should_process_with_context(
            document_items[1], 1, document_items
        )  # Too short
        assert not should_process_1
        should_process_2, _ = classifier.should_process_with_context(
            document_items[2], 2, document_items
        )  # Template
        assert not should_process_2

    def test_should_process_with_context_footer_section_edge_cases(self):
        """Test edge cases for footer section processing."""
        classifier = ContentClassifier()

        document_items = [
            "This is the first prose paragraph that should be skipped.",
            "This is the second prose paragraph that should be processed.",
            "==References==",  # This triggers footer section
            "| {| Some table content",  # Non-prose, non-heading content in footer section
        ]

        # Process items to get to footer section
        classifier.should_process_with_context(document_items[0], 0, document_items)
        classifier.should_process_with_context(document_items[1], 1, document_items)
        classifier.should_process_with_context(document_items[2], 2, document_items)

        should_process_3, skip_reason_3 = classifier.should_process_with_context(
            document_items[3], 3, document_items
        )
        assert not should_process_3
        assert skip_reason_3 == "Content in footer section"

    def test_is_footer_heading_edge_cases(self):
        """Test edge cases for footer heading detection."""
        classifier = ContentClassifier()

        # Test content that doesn't start with "==" (should return False immediately)
        assert not classifier._is_footer_heading("Not a heading")
        assert not classifier._is_footer_heading("This is regular text")
        assert not classifier._is_footer_heading("")
        assert not classifier._is_footer_heading("   ")

    def test_has_orphaned_closing_tags_no_orphaned(self):
        """Test _has_orphaned_closing_tags when no orphaned tags exist."""
        # Test content with no orphaned tags (should return False at the end)
        content_no_orphaned = "This is regular content with properly matched [[wikilinks]] and {{templates}}."
        assert not ContentClassifier._has_orphaned_closing_tags(content_no_orphaned)

        # Test content with matched tags
        assert not ContentClassifier._has_orphaned_closing_tags(
            "Content with <ref>citation</ref> and [[link]]"
        )

        # Test content with no special tags at all
        assert not ContentClassifier._has_orphaned_closing_tags(
            "Just plain text content here"
        )

    def test_get_non_processable_prose_reason_direct(self):
        """Test _get_non_processable_prose_reason method directly to hit all branches."""
        classifier = ContentClassifier()

        # Test empty content
        assert classifier._get_non_processable_prose_reason("") == "Empty content"
        assert classifier._get_non_processable_prose_reason("   ") == "Empty content"

        # Test non-prose content (heading, list items, etc.) - make sure they're long enough
        # Use content that starts with NON_PROSE_PREFIXES
        assert (
            classifier._get_non_processable_prose_reason(
                "==This is a sufficiently long heading that should be identified as non-prose=="
            )
            == "Non-prose content (heading, list, table, template, or media)"
        )
        assert (
            classifier._get_non_processable_prose_reason(
                "{{Template:This is a sufficiently long template call that should be identified as non-prose}}"
            )
            == "Non-prose content (heading, list, table, template, or media)"
        )
        assert (
            classifier._get_non_processable_prose_reason(
                "| This is a sufficiently long table row that should be identified as non-prose content"
            )
            == "Non-prose content (heading, list, table, template, or media)"
        )

        short_content = "A" * 47  # Just under MIN_PARAGRAPH_LENGTH (48)
        assert (
            classifier._get_non_processable_prose_reason(short_content)
            == "Content too short to process"
        )

        # Test content with categories
        content_with_category = "This is a sufficiently long paragraph with [[Category:Example]] that should be identified as having category links."
        assert (
            classifier._get_non_processable_prose_reason(content_with_category)
            == "Contains category links"
        )

        # Test the else branch (content classified as non-prose for other reasons)
        # Use content that's long enough, doesn't have categories, doesn't start with non-prose prefixes,
        # but would still be non-processable for other reasons (e.g., has invalid markup)
        # This content will be long enough, not match prefixes, not have categories, but be invalid
        invalid_markup_content = "This is a sufficiently long paragraph with unmatched [[wikilink that should be classified as non-prose due to invalid markup"
        assert (
            classifier._get_non_processable_prose_reason(invalid_markup_content)
            == "Content classified as non-prose"
        )

    def test_is_footer_heading_non_heading_content(self):
        """Test _is_footer_heading with content that doesn't start with '=='."""
        classifier = ContentClassifier()

        assert not classifier._is_footer_heading("This is regular prose content")
        assert not classifier._is_footer_heading(
            "Some random text without heading markers"
        )
        assert not classifier._is_footer_heading(
            "Text that mentions == but doesn't start with it"
        )

        # Test empty content
        assert not classifier._is_footer_heading("")
        assert not classifier._is_footer_heading("   ")

        # Test content starting with other markup
        assert not classifier._is_footer_heading("[[Link text]]")
        assert not classifier._is_footer_heading("{{Template call}}")
        assert not classifier._is_footer_heading("* List item")

    def test_first_prose_paragraph_only_skipped_in_lead_section(self):
        """Test that first prose paragraph is only skipped when in lead section."""
        classifier = ContentClassifier()

        # Test document with lead section followed by regular sections
        document_items = [
            "This is the first prose paragraph in lead section - should be skipped.",
            "This is the second prose paragraph in lead section - should be processed.",
            "== First Section ==",
            "This is the first prose paragraph in a regular section - should be processed.",
            "This is the second prose paragraph in a regular section - should be processed.",
            "== Second Section ==",
            "This is the first prose paragraph in another regular section - should be processed.",
        ]

        # Test first prose in lead section (should be skipped)
        should_process_0, skip_reason_0 = classifier.should_process_with_context(
            document_items[0], 0, document_items
        )
        assert not should_process_0, (
            "First prose paragraph in lead section should be skipped"
        )
        assert (
            skip_reason_0
            == "First prose paragraph in lead section - skipped to preserve article structure"
        )
        assert classifier.is_in_lead_section(), "Should still be in lead section"

        # Test second prose in lead section (should be processed)
        should_process_1, skip_reason_1 = classifier.should_process_with_context(
            document_items[1], 1, document_items
        )
        assert should_process_1, (
            "Second prose paragraph in lead section should be processed"
        )
        assert skip_reason_1 is None
        assert classifier.is_in_lead_section(), "Should still be in lead section"

        # Test section heading (should be skipped, marks end of lead section)
        should_process_2, skip_reason_2 = classifier.should_process_with_context(
            document_items[2], 2, document_items
        )
        assert not should_process_2, "Section heading should be skipped"
        assert not classifier.is_in_lead_section(), (
            "Should no longer be in lead section"
        )

        # Test first prose in regular section (should be processed, not skipped)
        should_process_3, skip_reason_3 = classifier.should_process_with_context(
            document_items[3], 3, document_items
        )
        assert should_process_3, (
            "First prose paragraph in regular section should be processed"
        )
        assert skip_reason_3 is None
        assert not classifier.is_in_lead_section(), "Should not be in lead section"

        # Test second prose in regular section (should be processed)
        should_process_4, skip_reason_4 = classifier.should_process_with_context(
            document_items[4], 4, document_items
        )
        assert should_process_4, (
            "Second prose paragraph in regular section should be processed"
        )
        assert skip_reason_4 is None

        # Test another section heading (should be skipped)
        should_process_5, skip_reason_5 = classifier.should_process_with_context(
            document_items[5], 5, document_items
        )
        assert not should_process_5, "Another section heading should be skipped"

        # Test first prose in another regular section (should be processed)
        should_process_6, skip_reason_6 = classifier.should_process_with_context(
            document_items[6], 6, document_items
        )
        assert should_process_6, (
            "First prose paragraph in another regular section should be processed"
        )
        assert skip_reason_6 is None

    def test_lead_section_tracking_with_level_2_headings(self):
        """Test that lead section tracking works correctly with level 2 headings."""
        classifier = ContentClassifier()

        # Test document with various heading levels
        document_items = [
            "This is the first lead prose paragraph that should be skipped because it is the very first prose content in the lead section.",
            "This is the second lead prose paragraph that should be processed because the first one was already skipped.",
            "=== Level 3 heading ===",  # Should not end lead section
            "This is the third lead prose paragraph that should be processed because we are still in the lead section.",
            "== Level 2 heading ==",  # Should end lead section
            "This is the first prose paragraph in a regular section and should be processed normally without skipping.",
        ]

        # Test first prose in lead section (should be skipped)
        should_process_0, _ = classifier.should_process_with_context(
            document_items[0], 0, document_items
        )
        assert not should_process_0, (
            "First prose paragraph in lead section should be skipped"
        )
        assert classifier.is_in_lead_section(), "Should be in lead section"

        # Test second prose in lead section (should be processed)
        should_process_1, skip_reason_1 = classifier.should_process_with_context(
            document_items[1], 1, document_items
        )
        assert should_process_1, (
            f"Second prose paragraph in lead section should be processed, but got skip reason: {skip_reason_1}"
        )
        assert classifier.is_in_lead_section(), "Should still be in lead section"

        # Test level 3 heading (should not end lead section)
        should_process_2, _ = classifier.should_process_with_context(
            document_items[2], 2, document_items
        )
        assert not should_process_2, "Level 3 heading should be skipped"
        assert classifier.is_in_lead_section(), (
            "Should still be in lead section after level 3 heading"
        )

        # Test prose still in lead section (should be processed, first prose already encountered)
        should_process_3, _ = classifier.should_process_with_context(
            document_items[3], 3, document_items
        )
        assert should_process_3, "Prose after level 3 heading should be processed"
        assert classifier.is_in_lead_section(), "Should still be in lead section"

        # Test level 2 heading (should end lead section)
        should_process_4, _ = classifier.should_process_with_context(
            document_items[4], 4, document_items
        )
        assert not should_process_4, "Level 2 heading should be skipped"
        assert not classifier.is_in_lead_section(), (
            "Should no longer be in lead section after level 2 heading"
        )

        # Test prose in regular section (should be processed)
        should_process_5, _ = classifier.should_process_with_context(
            document_items[5], 5, document_items
        )
        assert should_process_5, "Prose in regular section should be processed"
        assert not classifier.is_in_lead_section(), "Should not be in lead section"
