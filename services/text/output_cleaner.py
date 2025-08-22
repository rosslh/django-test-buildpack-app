"""LLM output cleaning for Wiki editing operations.

This module provides functionality to clean and normalize LLM output, removing common
artifacts and formatting issues.
"""

import re

# Constants for code block processing
CODE_FENCE_PATTERN = "```"
MAX_LANGUAGE_SPECIFIER_LENGTH = 15
UNCHANGED_MARKER = "<UNCHANGED>"


class OutputCleaner:
    """Handles cleaning of LLM output artifacts.

    Removes common artifacts from LLM responses such as code fences, language
    specifiers, and normalizes whitespace.
    """

    @staticmethod
    def cleanup_llm_output(text: str) -> str:
        """Clean LLM output by removing artifacts and normalizing whitespace.

        Args:
            text: Raw LLM output text

        Returns:
            Cleaned text with artifacts removed
        """
        stripped_text = text.strip()

        if OutputCleaner._is_code_fenced(stripped_text):
            stripped_text = OutputCleaner._process_code_fenced_content(stripped_text)

        # More robust check for UNCHANGED marker by stripping common wrapping characters
        cleaned_marker_check = stripped_text.strip("`'\"")
        if cleaned_marker_check == UNCHANGED_MARKER:
            return UNCHANGED_MARKER

        return OutputCleaner._normalize_whitespace(stripped_text)

    @staticmethod
    def _is_code_fenced(text: str) -> bool:
        """Check if text is wrapped in code fences."""
        return text.startswith(CODE_FENCE_PATTERN) and text.endswith(CODE_FENCE_PATTERN)

    @staticmethod
    def _process_code_fenced_content(text: str) -> str:
        """Process content that is wrapped in code fences."""
        content_between_fences = text[3:-3]  # Remove outer ```

        if OutputCleaner._contains_multiple_code_blocks(content_between_fences):
            return text

        return OutputCleaner._extract_content_from_code_block(content_between_fences)

    @staticmethod
    def _contains_multiple_code_blocks(content: str) -> bool:
        """Check if content contains multiple separate code blocks."""
        inner_content = content.strip()
        return (
            CODE_FENCE_PATTERN in inner_content
            and not inner_content.startswith(CODE_FENCE_PATTERN)
            and " and " in inner_content
        )

    @staticmethod
    def _extract_content_from_code_block(content: str) -> str:
        """Extract content from a single code block, handling language specifiers."""
        parts = content.split("\n", 1)
        first_line = parts[0].strip()

        if OutputCleaner._is_language_specifier(first_line):
            return parts[1].strip() if len(parts) > 1 else ""

        return content.strip()

    @staticmethod
    def _is_language_specifier(line: str) -> bool:
        """Check if a line appears to be a language specifier."""
        return (
            bool(line)
            and not re.search(r"\s", line)
            and len(line) < MAX_LANGUAGE_SPECIFIER_LENGTH
            and UNCHANGED_MARKER.lower() not in line.lower()
        )

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize whitespace by removing double spaces and trimming."""
        return re.sub(r" +", " ", text).strip()
