import re
from collections import Counter
from typing import List, Optional, Tuple

from services.validation.base_validator import BaseValidator


class QuoteValidator(BaseValidator):
    """Handles validation of quoted text."""

    def validate_and_correct(
        self,
        original_text: str,
        edited_text: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> Tuple[str, bool]:
        """Validate that quoted text has not been removed, added or modified.

        Also handles restoration of italic and bold formatting.

        Returns corrected text and a boolean indicating if a revert is needed.
        """
        working_text = edited_text

        working_text = self._handle_wikitext_quotes(original_text, working_text)

        # Handle restoration of italic and bold formatting
        working_text = self._restore_italic_bold_formatting(original_text, working_text)

        # Handle double quotes only
        original_double_quotes = re.findall(r'"(.*?)"', original_text)
        edited_double_quotes = re.findall(r'"(.*?)"', working_text)

        # Check double quotes
        if Counter(original_double_quotes) != Counter(edited_double_quotes):
            if not self._are_quotes_equivalent_with_punctuation(
                original_double_quotes, edited_double_quotes
            ):
                corrected_text = self._handle_quote_changes(
                    working_text, original_double_quotes, edited_double_quotes, '"'
                )
                if corrected_text is None:
                    # Need to revert
                    return original_text, True
                working_text = corrected_text

        return working_text, False

    def _handle_wikitext_quotes(self, original_text: str, working_text: str) -> str:
        # Check for italics/bold changed to double quotes
        for quote_content in re.findall(r'"(.*?)"', working_text):
            # Check for '''bold''' version in original (check bold first to avoid substring issues)
            bold_version = f"'''{quote_content}'''"
            if bold_version in original_text:
                working_text = working_text.replace(f'"{quote_content}"', bold_version)
                continue
            # Check for ''italic'' version in original
            italic_version = f"''{quote_content}''"
            if italic_version in original_text:
                working_text = working_text.replace(
                    f'"{quote_content}"', italic_version
                )

        return working_text

    def _restore_italic_bold_formatting(
        self, original_text: str, working_text: str
    ) -> str:
        """Restore italic and bold formatting when display text is still present."""
        # First handle bold formatting (3 apostrophes) to avoid conflicts with italic
        bold_matches = re.findall(r"'''(.*?)'''", original_text, re.DOTALL)
        for bold_content in bold_matches:
            bold_formatted = f"'''{bold_content}'''"
            # If the formatted version is not in working text but plain text is
            if bold_formatted not in working_text and bold_content in working_text:
                # Check each occurrence individually
                working_text = self._restore_formatting_for_content(
                    working_text, bold_content, bold_formatted, "bold"
                )

        # Then handle italic formatting (2 apostrophes)
        italic_matches = re.findall(r"''(.*?)''", original_text, re.DOTALL)
        for italic_content in italic_matches:
            italic_formatted = f"''{italic_content}''"
            # If the formatted version is not in working text but plain text is
            if italic_formatted not in working_text and italic_content in working_text:
                # Check each occurrence individually
                working_text = self._restore_formatting_for_content(
                    working_text, italic_content, italic_formatted, "italic"
                )

        return working_text

    def _restore_formatting_for_content(
        self,
        working_text: str,
        target: str,
        formatted_target: str,
        format_type: str,
    ) -> str:
        """Restore formatting for each occurrence of target content individually."""
        # Find all occurrences and process them from right to left to avoid position shifts
        positions = []
        start = 0
        while True:
            pos = working_text.find(target, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        # Process from right to left to avoid position shifts
        for pos in reversed(positions):
            # Check if this specific occurrence is safe to format
            if (
                not self._is_within_formatting_block(working_text, pos, target)
                and not self._would_create_invalid_syntax(working_text, pos, target)
                and not self._is_within_quotes(working_text, pos, target, "'")
            ):
                # Use word boundary replacement for this specific occurrence
                before_text = working_text[:pos]
                after_text = working_text[pos + len(target) :]

                # Check if this is a word boundary match
                escaped_target = re.escape(target)
                pattern = r"\b" + escaped_target + r"\b"
                match = re.search(pattern, working_text[pos : pos + len(target)])

                if match:
                    working_text = before_text + formatted_target + after_text

        return working_text

    def _is_within_formatting_block(self, text: str, pos: int, target: str) -> bool:
        target_end = pos + len(target)
        all_blocks = (
            self._find_italic_blocks(text)
            + self._find_bold_blocks(text)
            + self._find_quote_blocks(text)
            + self._find_square_bracket_blocks(text)
            + self._find_template_blocks(text)
            + self._find_reference_blocks(text)
            + self._find_nowiki_blocks(text)
            + self._find_html_tag_blocks(text)
            + self._find_comment_blocks(text)
            + self._find_external_link_blocks(text)
        )
        for block_start, block_end in all_blocks:
            if block_start < pos and target_end < block_end:
                return True
        return False

    def _find_italic_blocks(self, text):
        return [
            (m.start(), m.end()) for m in re.finditer(r"''(.*?)''", text, re.DOTALL)
        ]

    def _find_bold_blocks(self, text):
        return [
            (m.start(), m.end()) for m in re.finditer(r"'''(.*?)'''", text, re.DOTALL)
        ]

    def _find_quote_blocks(self, text):
        return [(m.start(), m.end()) for m in re.finditer(r'"(.*?)"', text, re.DOTALL)]

    def _find_square_bracket_blocks(self, text):
        return [
            (m.start(), m.end()) for m in re.finditer(r"\[\[(.*?)\]\]", text, re.DOTALL)
        ]

    def _find_template_blocks(self, text):
        return [
            (m.start(), m.end()) for m in re.finditer(r"\{\{(.*?)\}\}", text, re.DOTALL)
        ]

    def _find_reference_blocks(self, text):
        return [
            (m.start(), m.end())
            for m in re.finditer(
                r"<ref[^>]*>(.*?)</ref>", text, re.DOTALL | re.IGNORECASE
            )
        ]

    def _find_nowiki_blocks(self, text):
        return [
            (m.start(), m.end())
            for m in re.finditer(
                r"<nowiki[^>]*>(.*?)</nowiki>", text, re.DOTALL | re.IGNORECASE
            )
        ]

    def _find_html_tag_blocks(self, text):
        blocks = []
        for tag in ["code", "pre", "math", "syntaxhighlight"]:
            for m in re.finditer(
                rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE
            ):
                blocks.append((m.start(), m.end()))
        return blocks

    def _find_comment_blocks(self, text):
        return [
            (m.start(), m.end()) for m in re.finditer(r"<!--(.*?)-->", text, re.DOTALL)
        ]

    def _find_external_link_blocks(self, text):
        return [
            (m.start(), m.end())
            for m in re.finditer(r"\[https?://[^\]]*\]", text, re.DOTALL)
        ]

    def _would_create_invalid_syntax(self, text: str, pos: int, target: str) -> bool:
        """Check if adding formatting to target at pos would create invalid nested syntax."""
        target_end = pos + len(target)

        # Check for adjacent formatting markers that would create invalid syntax
        # Look for formatting markers immediately before the target (allowing for whitespace)
        before_text = text[:pos].rstrip()
        if before_text.endswith("''"):
            # Target is after italic/bold closing marker (with possible whitespace)
            # Note: This covers both '' and ''' cases since ''' ends with ''
            return True
        if before_text.endswith('"'):
            # Target is after quote marker (with possible whitespace)
            return True

        # Look for formatting markers immediately after the target (allowing for whitespace)
        after_text = text[target_end:].lstrip()
        if after_text.startswith("''"):
            # Target is before italic/bold opening marker (with possible whitespace)
            # Note: This covers both '' and ''' cases since ''' starts with ''
            return True
        if after_text.startswith('"'):
            # Target is before quote marker (with possible whitespace)
            return True

        # Note: The between-markers checks were removed as they were unreachable.
        # If before_text.endswith() matched any marker, we would have already returned True above.

        return False

    def _is_within_quotes(
        self, text: str, pos: int, target: str, quote_char: str
    ) -> bool:
        """Check if target at pos is within quotes."""
        if pos > 0 and text[pos - 1] == quote_char:
            end_pos = pos + len(target)
            remaining_text = text[end_pos:]
            if quote_char in remaining_text:
                quote_pos = remaining_text.find(quote_char)
                between_text = remaining_text[:quote_pos]
                return re.match(r"^[^\w]*$", between_text) is not None
        return False

    def _handle_quote_changes(
        self,
        working_text: str,
        original_quotes: List[str],
        edited_quotes: List[str],
        quote_char: str,
    ) -> Optional[str]:
        original_counts = Counter(original_quotes)
        edited_counts = Counter(edited_quotes)
        removed = list((original_counts - edited_counts).elements())
        added = list((edited_counts - original_counts).elements())

        # If quotes were only added, remove them but keep the text
        if added and not removed:
            for quote_content in added:
                working_text = working_text.replace(
                    f"{quote_char}{quote_content}{quote_char}", quote_content
                )
            return working_text

        # If quotes were only removed, try to re-add them
        if removed and not added:
            any_restored = False
            missing_quotes = []

            for quote_content in removed:
                if quote_content in working_text:
                    # Handle each occurrence individually
                    old_text = working_text
                    working_text = self._restore_quotes_for_content(
                        working_text, quote_content, quote_char
                    )
                    # Check if any quotes were actually restored for this content
                    if working_text != old_text:
                        any_restored = True
                    else:
                        missing_quotes.append(quote_content)
                else:
                    # Quote text is completely missing
                    missing_quotes.append(quote_content)

            # If we restored at least some quotes, return the result
            # Only revert if no quotes could be restored at all
            if any_restored:
                return working_text
            elif missing_quotes:
                # No quotes could be restored, trigger revert
                return None
        return None

    def _restore_quotes_for_content(
        self, working_text: str, target: str, quote_char: str
    ) -> str:
        """Restore quotes for each occurrence of target content individually."""
        # Find all occurrences and process them from right to left to avoid position shifts
        positions = []
        start = 0
        while True:
            pos = working_text.find(target, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        # Process from right to left to avoid position shifts
        for pos in reversed(positions):
            # Check if this specific occurrence is safe to quote
            if not self._is_within_formatting_block(
                working_text, pos, target
            ) and not self._would_create_invalid_syntax(working_text, pos, target):
                # Replace this specific occurrence
                before_text = working_text[:pos]
                after_text = working_text[pos + len(target) :]
                working_text = (
                    before_text + f"{quote_char}{target}{quote_char}" + after_text
                )

        return working_text

    def _format_revert_message(self, added: List[str], removed: List[str]) -> str:
        message = "WARNING: Quotes were modified."
        if removed:
            message += f" Removed: {removed}"
        if added:
            message += f" Added: {added}"
        message += ". Reverting."
        return message

    def _are_quotes_equivalent_with_punctuation(
        self, quotes1: List[str], quotes2: List[str]
    ) -> bool:
        """Check if two lists of quotes are equivalent with trailing punctuation."""
        if len(quotes1) != len(quotes2):
            return False

        for q1, q2 in zip(quotes1, quotes2, strict=False):
            if q1 != q2:
                # Check if q2 is q1 with trailing punctuation
                if not (q2.startswith(q1) and re.match(r"^[^\w]*$", q2[len(q1) :])):
                    # Check if q1 is q2 with trailing punctuation
                    if not (q1.startswith(q2) and re.match(r"^[^\w]*$", q1[len(q2) :])):
                        return False

        return True
