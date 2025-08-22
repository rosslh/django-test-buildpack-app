"""Tests for the DocumentParser module.

This module tests the DocumentParser functionality to ensure proper parsing of wikitext
documents into structured items.
"""

from services.document.parser import DocumentParser


class TestDocumentParser:
    """Test cases for DocumentParser class."""

    def test_process_delegates_to_parse_document_structure(self):
        """Test that process method delegates to parse_document_structure."""
        parser = DocumentParser()
        # Simple test to ensure process calls parse_document_structure
        result = parser.process(
            "Simple paragraph text that is long enough to be processed."
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_parse_multiline_template_block(self):
        """Test parsing of multiline template blocks."""
        parser = DocumentParser()
        text = """{{Template
|param1=value1
|param2=value2
}}

Next paragraph content that is long enough to be considered proper prose content."""

        result = parser.parse_document_structure(text)
        # Should have template block as one item and paragraph as another
        assert len(result) >= 2
        assert "{{Template" in result[0]
        # Find the paragraph in the results
        paragraph_found = False
        for item in result:
            if "Next paragraph" in item:
                paragraph_found = True
                break
        assert paragraph_found, f"Could not find paragraph in results: {result}"

    def test_parse_multiline_blockquote_block(self):
        """Test parsing of multiline blockquote blocks."""
        parser = DocumentParser()
        text = """<blockquote>
This is a long blockquote that spans multiple lines
and contains substantial content for testing purposes.
</blockquote>

Next paragraph content that is long enough to be considered proper prose content."""

        result = parser.parse_document_structure(text)
        # Should have blockquote block as one item and paragraph as another
        assert len(result) >= 2
        assert "<blockquote>" in result[0]
        # Find the paragraph in the results
        paragraph_found = False
        for item in result:
            if "Next paragraph" in item:
                paragraph_found = True
                break
        assert paragraph_found, f"Could not find paragraph in results: {result}"

    def test_single_line_template_block(self):
        """Test parsing of single-line template blocks."""
        parser = DocumentParser()
        text = """{{Template|param=value}}

Next paragraph content that is long enough to be considered proper prose content."""

        result = parser.parse_document_structure(text)
        assert len(result) >= 2
        assert "{{Template|param=value}}" == result[0].strip()

    def test_single_line_blockquote_block(self):
        """Test parsing of single-line blockquote blocks."""
        parser = DocumentParser()
        text = """<blockquote>Short quote</blockquote>

Next paragraph content that is long enough to be considered proper prose content."""

        result = parser.parse_document_structure(text)
        assert len(result) >= 2
        assert "<blockquote>Short quote</blockquote>" == result[0].strip()

    def test_determine_block_type(self):
        """Test block type determination."""
        parser = DocumentParser()
        assert parser._determine_block_type("{{Template") == "template"
        assert parser._determine_block_type("<blockquote>") == "blockquote"

    def test_is_single_line_block(self):
        """Test single line block detection."""
        parser = DocumentParser()
        # Template tests
        assert parser._is_single_line_block("{{Template|param=value}}", "{{")
        assert not parser._is_single_line_block("{{Template", "{{")

        # Blockquote tests
        assert parser._is_single_line_block(
            "<blockquote>Quote</blockquote>", "<blockquote>"
        )
        assert not parser._is_single_line_block("<blockquote>Quote", "<blockquote>")

    def test_is_block_terminator(self):
        """Test block terminator detection."""
        parser = DocumentParser()

        # Test header terminators
        assert parser._is_block_terminator("==Header==", "{{")
        assert parser._is_block_terminator("==Header==", "<blockquote>")

        # Test category terminators
        assert parser._is_block_terminator("[[Category:Example]]", "{{")
        assert parser._is_block_terminator("[[Category:Example]]", "<blockquote>")

        # Test file terminators
        assert parser._is_block_terminator("[[File:example.jpg]]", "{{")
        assert parser._is_block_terminator("[[File:example.jpg]]", "<blockquote>")

        # Test conflicting block types
        assert parser._is_block_terminator("{{Template", "<blockquote>")
        assert parser._is_block_terminator("<blockquote>", "{{")

        # Test non-terminators
        assert not parser._is_block_terminator("Regular content", "{{")
        assert not parser._is_block_terminator("Regular content", "<blockquote>")

    def test_is_block_closed_template(self):
        """Test template block closure detection."""
        parser = DocumentParser()

        # Properly closed template
        assert parser._is_block_closed(
            "{{Template|param=value}}", "|param=value}}", "{{"
        )

        # Not closed template
        assert not parser._is_block_closed(
            "{{Template|param=value", "|param=value", "{{"
        )

        # Nested templates - properly closed
        full_text = "{{Outer|{{Inner|value}}}}"
        current_line = "{{Inner|value}}}}"
        assert parser._is_block_closed(full_text, current_line, "{{")

    def test_is_block_closed_blockquote(self):
        """Test blockquote block closure detection."""
        parser = DocumentParser()

        # Properly closed blockquote
        assert parser._is_block_closed(
            "Some content</blockquote>", "content</blockquote>", "<blockquote>"
        )

        # Not closed blockquote
        assert not parser._is_block_closed("Some content", "content", "<blockquote>")

    def test_multiline_template_block_terminated_early_by_header(self):
        """Test multiline template block terminated early by header."""

        parser = DocumentParser()
        text = """{{Template
|param1=value1
==Header==
More content"""

        result = parser.parse_document_structure(text)
        # Should have incomplete template block and header as separate items
        assert len(result) >= 2
        assert "{{Template" in result[0]
        assert "==Header==" in result[1]

    def test_multiline_blockquote_terminated_early_by_category(self):
        """Test multiline blockquote terminated early by category."""

        parser = DocumentParser()
        text = """<blockquote>
This is a quote that gets interrupted
[[Category:Example]]
More content"""

        result = parser.parse_document_structure(text)
        # Should have incomplete blockquote and category as separate items
        assert len(result) >= 2
        assert "<blockquote>" in result[0] and "[[Category:Example]]" not in result[0]
        assert "[[Category:Example]]" in result[1]

    def test_multiline_template_terminated_early_by_conflicting_blockquote(self):
        """Test multiline template terminated early by conflicting blockquote."""

        parser = DocumentParser()
        text = """{{Template
|param1=value1
<blockquote>
Conflicting content"""

        result = parser.parse_document_structure(text)
        # Should have incomplete template and blockquote as separate items
        assert len(result) >= 2
        assert "{{Template" in result[0] and "<blockquote>" not in result[0]
        assert "<blockquote>" in result[1]

    def test_multiline_blockquote_terminated_early_by_conflicting_template(self):
        """Test multiline blockquote terminated early by conflicting template."""

        parser = DocumentParser()
        text = """<blockquote>
This is a quote
{{Template
More content"""

        result = parser.parse_document_structure(text)
        # Should have incomplete blockquote and template as separate items
        assert len(result) >= 2
        assert "<blockquote>" in result[0] and "{{Template" not in result[0]
        assert "{{Template" in result[1]

    def test_multiline_template_block_reaches_end_without_closure(self):
        """Test multiline template that reaches end of document without closure."""
        parser = DocumentParser()
        text = """{{Template
|param1=value1
|param2=value2
Final line without closure"""

        result = parser.parse_document_structure(text)
        # Should have the incomplete template as one block
        assert len(result) >= 1
        assert "{{Template" in result[0]
        assert "Final line without closure" in result[0]

    def test_multiline_block_conflicting_type_detection_in_content_parser(self):
        """Test conflicting block type detection within
        _parse_multiline_block_content."""

        parser = DocumentParser()

        # Create a scenario where _is_block_terminator doesn't catch the conflict
        # but _parse_multiline_block_content does
        # We need to patch _is_block_terminator to return False for the conflicting line
        import unittest.mock

        def mock_is_block_terminator(content, block_start_token):
            # Let the conflicting blockquote line pass through _is_block_terminator
            if "<blockquote>" in content and block_start_token == "{{":
                return False
            return parser.__class__._is_block_terminator(
                parser, content, block_start_token
            )

        with unittest.mock.patch.object(
            parser, "_is_block_terminator", side_effect=mock_is_block_terminator
        ):
            text = """{{Template
|param1=value1
<blockquote>
More content"""

            result = parser.parse_document_structure(text)
            # Should have template block that was terminated by conflicting type
            assert len(result) >= 1
            assert "{{Template" in result[0]

    # Test from test_processing.py
    def test_document_parser_parse_document_structure_prose(self):
        parser = DocumentParser()
        text = "This is a prose paragraph.\n\nThis is another prose paragraph."
        result = parser.parse_document_structure(text)
        assert len(result) == 3
        assert result[0] == "This is a prose paragraph."
        assert result[1] == ""
        assert result[2] == "This is another prose paragraph."
