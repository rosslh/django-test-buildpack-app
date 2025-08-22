"""Document parser for Wiki editing operations.

This module provides functionality for parsing wikitext documents into structured items.
"""

from typing import List, Tuple

from services.utils.text_utils import split_into_paragraphs

# Constants for document parsing
TEMPLATE_START_TOKEN = "{{"
TEMPLATE_END_TOKEN = "}}"
BLOCKQUOTE_START_TOKEN = "<blockquote>"
BLOCKQUOTE_END_TOKEN = "</blockquote>"

# Block termination markers
BLOCK_TERMINATORS = ["==", "[[Category:", "[[File:"]


class DocumentParser:
    """Handles parsing and structuring of wikitext documents.

    Parses wikitext into structured items, handling both prose content and special wiki
    elements like templates and blockquotes.
    """

    def process(self, text: str) -> List[str]:
        """Process document content into structured items.

        This method implements the IDocumentProcessor interface.

        Args:
            text: Raw wikitext to parse

        Returns:
            List of document sections as strings
        """
        return self.parse_document_structure(text)

    def parse_document_structure(self, text: str) -> List[str]:
        """Parse document into structured items.

        Handles both prose and non-prose blocks, preserving the structure
        of templates, blockquotes, and other wiki elements.

        Args:
            text: Raw wikitext to parse

        Returns:
            List of document sections as strings
        """
        raw_paragraphs = split_into_paragraphs(text)
        items_to_process_or_preserve = []
        current_index = 0
        while current_index < len(raw_paragraphs):
            paragraph_content = raw_paragraphs[current_index]
            stripped_content = paragraph_content.strip()
            if not stripped_content:
                items_to_process_or_preserve.append(paragraph_content)
                current_index += 1
                continue
            # If this is a multi-line block start (template or blockquote)
            if stripped_content.startswith(
                TEMPLATE_START_TOKEN
            ) or stripped_content.startswith(BLOCKQUOTE_START_TOKEN):
                block_content, new_index, block_terminated_early = (
                    self._parse_multiline_block(
                        raw_paragraphs, current_index, stripped_content
                    )
                )
                items_to_process_or_preserve.append(block_content)
                if block_terminated_early:
                    current_index = new_index
                else:
                    current_index = new_index
            else:
                # Always treat headers, prose, and other non-block lines as separate
                # items
                items_to_process_or_preserve.append(paragraph_content)
                current_index += 1
        return items_to_process_or_preserve

    def _parse_multiline_block(
        self, raw_paragraphs: List[str], start_index: int, first_line_content: str
    ) -> Tuple[str, int, bool]:
        """Parse a multi-line block such as a template or blockquote."""
        block_type = self._determine_block_type(first_line_content)
        block_start_token = (
            TEMPLATE_START_TOKEN if block_type == "template" else BLOCKQUOTE_START_TOKEN
        )
        if self._is_single_line_block(first_line_content, block_start_token):
            return first_line_content, start_index + 1, False
        return self._parse_multiline_block_content(
            raw_paragraphs, start_index, block_start_token, first_line_content
        )

    def _parse_multiline_block_content(
        self,
        raw_paragraphs: List[str],
        start_index: int,
        block_start_token: str,
        initial_content: str,
    ) -> Tuple[str, int, bool]:
        """Parse the content of a multi-line block.

        Returns (block_text, next_index, terminated_early).
        """
        block_lines = [initial_content]
        full_block_text = initial_content
        current_index = start_index + 1
        terminated_early = False
        while current_index < len(raw_paragraphs):
            current_line = raw_paragraphs[current_index]
            stripped_line = current_line.strip()
            # If a block terminator is encountered (for blockquotes/templates), break
            # (do not include this line)
            if self._is_block_terminator(current_line, block_start_token):
                terminated_early = True
                break
            # If a conflicting block type is encountered, break (do not include this
            # line)
            if (
                block_start_token == TEMPLATE_START_TOKEN
                and stripped_line.startswith(BLOCKQUOTE_START_TOKEN)
            ) or (
                block_start_token == BLOCKQUOTE_START_TOKEN
                and stripped_line.startswith(TEMPLATE_START_TOKEN)
            ):
                terminated_early = True
                break
            block_lines.append(current_line)
            full_block_text += "\n" + current_line
            # If the block is closed, include this line and break
            if self._is_block_closed(full_block_text, current_line, block_start_token):
                current_index += 1
                return "\n".join(block_lines), current_index, False
            current_index += 1
        block_text = "\n".join(block_lines)
        return block_text, current_index, terminated_early

    def _determine_block_type(self, content: str) -> str:
        """Determine block type from its starting token."""
        return "template" if content.startswith(TEMPLATE_START_TOKEN) else "blockquote"

    def _is_single_line_block(self, content: str, block_start_token: str) -> bool:
        """Check if a block is contained on a single line."""
        end_token = (
            TEMPLATE_END_TOKEN
            if block_start_token == TEMPLATE_START_TOKEN
            else BLOCKQUOTE_END_TOKEN
        )
        return end_token in content

    def _is_block_terminator(self, content: str, block_start_token: str) -> bool:
        """Check if a line should terminate the current block parsing.

        Templates are not terminated by these markers. Also terminates if a conflicting
        block type is encountered.
        """
        stripped = content.strip()
        # Block terminators (headers, categories, files)
        if any(stripped.startswith(marker) for marker in BLOCK_TERMINATORS):
            return True
        # Conflicting block types
        if block_start_token == TEMPLATE_START_TOKEN and stripped.startswith(
            BLOCKQUOTE_START_TOKEN
        ):
            return True
        if block_start_token == BLOCKQUOTE_START_TOKEN and stripped.startswith(
            TEMPLATE_START_TOKEN
        ):
            return True
        return False

    def _is_block_closed(
        self, full_block_text: str, current_line: str, block_start_token: str
    ) -> bool:
        """Check if a block is properly closed."""
        if block_start_token == TEMPLATE_START_TOKEN:
            start_token_count = full_block_text.count(TEMPLATE_START_TOKEN)
            end_token_count = full_block_text.count(TEMPLATE_END_TOKEN)
            # Only closed if counts are equal and current line ends with }}
            return (
                start_token_count > 0
                and start_token_count == end_token_count
                and current_line.strip().endswith(TEMPLATE_END_TOKEN)
            )
        end_token = BLOCKQUOTE_END_TOKEN
        return end_token in current_line
