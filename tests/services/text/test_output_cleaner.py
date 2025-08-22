"""Tests for LLM output cleaner.

This module tests the LLMOutputCleaner functionality.
"""

import pytest

from services.text.output_cleaner import OutputCleaner


class TestLLMOutputCleaner:
    """Test cases for LLMOutputCleaner class."""

    def test_contains_multiple_code_blocks_true(self):
        """Test detection of multiple code blocks."""
        # Content with multiple code blocks (this is the content INSIDE the outer
        # fences)
        content = "python\ncode1\n``` and ```javascript\ncode2"
        assert OutputCleaner._contains_multiple_code_blocks(content)

    def test_contains_multiple_code_blocks_false_single_block(self):
        """Test detection when there's only one code block."""
        content = "```python\ncode\n```"
        assert not OutputCleaner._contains_multiple_code_blocks(content)

    def test_contains_multiple_code_blocks_false_no_and(self):
        """Test detection when there's no 'and' keyword."""
        content = "```python\ncode1\n``` or ```javascript\ncode2\n```"
        assert not OutputCleaner._contains_multiple_code_blocks(content)

    def test_contains_multiple_code_blocks_false_starts_with_fence(self):
        """Test detection when content starts with code fence."""
        content = "```python\ncode\n``` and more content"
        assert not OutputCleaner._contains_multiple_code_blocks(content)

    def test_is_language_specifier_false_contains_unchanged(self):
        """Test language specifier detection with UNCHANGED marker."""
        assert not OutputCleaner._is_language_specifier("<UNCHANGED>")
        # Note: "unchanged" by itself would be considered a language specifier since it doesn't contain "<UNCHANGED>"
        # Let's test with the actual marker format
        assert not OutputCleaner._is_language_specifier("text with <unchanged> marker")
        assert not OutputCleaner._is_language_specifier("contains <UNCHANGED> marker")

    def test_extract_content_from_code_block_with_empty_second_part(self):
        """Test extracting content when second part is empty after language
        specifier."""
        content = "python\n"
        result = OutputCleaner._extract_content_from_code_block(content)
        assert result == ""

        # Also test with just a language specifier and no newline
        content = "python"
        result = OutputCleaner._extract_content_from_code_block(content)
        assert result == ""

    def test_process_code_fenced_content_with_multiple_blocks_returns_original(self):
        """Test that multiple code blocks returns original text."""
        text = "```python\ncode1\n``` and ```javascript\ncode2\n```"
        result = OutputCleaner._process_code_fenced_content(text)
        assert result == text

    @pytest.mark.parametrize(
        "unchanged_input",
        [
            "`<UNCHANGED>`",
            "'<UNCHANGED>'",
            '"<UNCHANGED>"',
            " `<UNCHANGED>` ",
            " \n'<UNCHANGED>'\n ",
            '"`<UNCHANGED>`"',
            "'`<UNCHANGED>`'",
        ],
    )
    def test_cleanup_llm_output_wrapped_unchanged_marker(self, unchanged_input):
        """Test conversion of wrapped unchanged marker."""
        result = OutputCleaner.cleanup_llm_output(unchanged_input)
        assert result == "<UNCHANGED>"

    # Test from test_processing.py
    @pytest.mark.parametrize(
        "llm_response_unchanged",
        [
            "```\n<UNCHANGED>\n```",
            "```<UNCHANGED>```",
            "```wikitext\n<UNCHANGED>\n```",
            "```json\n<UNCHANGED>\n```",
            "``` \n<UNCHANGED>\n ```",
            "```<UNCHANGED>\n```",
            "```\n<UNCHANGED>```",
        ],
    )
    def test_cleanup_llm_output_handles_unchanged_signal(self, llm_response_unchanged):
        cleaned_output = OutputCleaner.cleanup_llm_output(llm_response_unchanged)
        assert cleaned_output == "<UNCHANGED>"

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("This  is   a   test", "This is a test"),
            ("   Leading and trailing   ", "Leading and trailing"),
            ("Multiple     spaces   inside", "Multiple spaces inside"),
            ("NoExtraSpaces", "NoExtraSpaces"),
            (" ", ""),
            ("", ""),
        ],
    )
    def test_normalize_whitespace(self, input_text, expected):
        """Test whitespace normalization removes extra spaces and trims."""
        assert OutputCleaner._normalize_whitespace(input_text) == expected

    def test_cleanup_llm_output_code_fenced_normalization(self):
        # Input is code-fenced, not unchanged, and needs whitespace normalization
        input_text = "```\nSome   code   here\n```"
        # After removing code fences, normalization should be applied
        # _process_code_fenced_content will remove the fences and not treat as unchanged
        expected = "Some code here"
        result = OutputCleaner.cleanup_llm_output(input_text)
        assert result == expected
