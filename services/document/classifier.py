"""Content classification for Wiki editing operations.

This module provides functionality for classifying wikitext content to determine if it
should be processed or preserved as-is.
"""

from typing import List, Optional, Tuple

import wikitextparser as wtp

from services.core.constants import (
    FOOTER_HEADINGS,
    MIN_PARAGRAPH_LENGTH,
    NON_PROSE_PREFIXES,
)
from services.core.interfaces import IContentClassifier
from services.utils.wiki_utils import contains_categories, is_prose_content


class ContentClassifier(IContentClassifier):
    """Classifies wikitext content for processing decisions.

    Maintains state to apply business rules about document structure,
    such as skipping first prose paragraphs and footer sections.
    """

    def __init__(self):
        self.reset_state()

    def reset_state(self) -> None:
        """Reset internal state for processing a new document."""
        self._first_prose_encountered = False
        self._in_footer_section = False
        self._in_lead_section = True

    def should_process_with_context(
        self, content: str, index: int, document_items: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Determine if content should be processed considering document context.

        Applies all business rules:
        - Content must be processable prose
        - Skip first prose paragraph in lead section only
        - Skip content in footer sections

        Args:
            content: The content to evaluate
            index: Position of content in the document
            document_items: All items in the document for context

        Returns:
            Tuple of (should_process, skip_reason):
            - should_process: True if content should be processed, False otherwise
            - skip_reason: Explanation if should_process is False, None if should_process is True
        """
        # Check if we're entering a section (level 2 heading) - this ends the lead section
        if self._is_level_2_heading(content):
            self._in_lead_section = False

        # Check if we've entered a footer section
        if self._is_footer_heading(content):
            self._in_footer_section = True

        # Skip content in footer sections
        if self._in_footer_section:
            content_type = self.get_content_type(content)
            if content_type == "footer-heading":
                return False, "Footer heading"
            elif content_type == "prose":
                return (
                    False,
                    "Prose content in footer section - skipped per editorial guidelines",
                )
            else:
                return False, "Content in footer section"

        # Check if content is processable prose
        if not self.is_processable_prose(content):
            return False, self._get_non_processable_prose_reason(content)

        # Skip first prose paragraph only in lead section
        if self._in_lead_section and not self._first_prose_encountered:
            self._first_prose_encountered = True
            return (
                False,
                "First prose paragraph in lead section - skipped to preserve article structure",
            )

        return True, None

    def get_content_type(self, content: str) -> str:
        """Get the type of content.

        Args:
            content: The content to classify

        Returns:
            String describing the content type
        """
        trimmed_content = content.strip()

        # Check for footer headings first (most specific)
        if self._is_footer_heading(content):
            return "footer-heading"

        # Check for regular headings
        elif trimmed_content.startswith("=="):
            return "heading"

        # Check for non-prose markers
        elif any(trimmed_content.startswith(prefix) for prefix in NON_PROSE_PREFIXES):
            return "non-prose"

        # Check for processable prose content
        elif (
            trimmed_content
            and len(trimmed_content) >= MIN_PARAGRAPH_LENGTH
            and is_prose_content(trimmed_content)
            and not contains_categories(trimmed_content)
        ):
            return "prose"

        else:
            return "other"

    def is_in_footer_section(self) -> bool:
        """Check if the classifier is currently in a footer section.

        Returns:
            True if currently processing content in a footer section, False otherwise
        """
        return self._in_footer_section

    def has_first_prose_been_encountered(self) -> bool:
        """Check if the first prose paragraph has been encountered.

        Returns:
            True if the first prose paragraph has been encountered, False otherwise
        """
        return self._first_prose_encountered

    def is_in_lead_section(self) -> bool:
        """Check if the classifier is currently in the lead section.

        Returns:
            True if currently processing content in the lead section, False otherwise
        """
        return self._in_lead_section

    def _get_non_processable_prose_reason(self, content: str) -> str:
        """Get the reason why content is not processable prose."""
        stripped_content = content.strip()
        if not stripped_content:
            return "Empty content"
        elif any(stripped_content.startswith(prefix) for prefix in NON_PROSE_PREFIXES):
            return "Non-prose content (heading, list, table, template, or media)"
        elif len(stripped_content) < MIN_PARAGRAPH_LENGTH:
            return "Content too short to process"
        elif contains_categories(stripped_content):
            return "Contains category links"
        else:
            return "Content classified as non-prose"

    def _is_footer_heading(self, content: str) -> bool:
        """Check if content is a footer heading.

        Args:
            content: The content to check

        Returns:
            True if content is a footer heading, False otherwise
        """
        if not content.strip().startswith("=="):
            return False
        # Normalize heading by removing '==' and whitespace, and lowercasing
        heading = content.strip().replace("=", "").strip().lower()
        return heading in FOOTER_HEADINGS

    def _is_level_2_heading(self, content: str) -> bool:
        """Check if content is a level 2 heading (== Section ==).

        Args:
            content: The content to check

        Returns:
            True if content is a level 2 heading, False otherwise
        """
        stripped_content = content.strip()
        # Check if it starts with exactly two equals signs
        if not stripped_content.startswith("=="):
            return False
        # Check if it's not a higher level heading (more than 2 equals signs)
        if stripped_content.startswith("==="):
            return False
        # Check if it ends with exactly two equals signs
        return stripped_content.endswith("==") and not stripped_content.endswith("===")

    def is_processable_prose(self, content: str) -> bool:
        """Determine if a string is processable prose content.

        Args:
            content: The string to check

        Returns:
            True if the content is considered processable prose, False otherwise.
        """
        return self.get_content_type(content) == "prose"

    @staticmethod
    def _has_orphaned_closing_tags(content: str) -> bool:
        """Check for orphaned closing tags (closing tags without corresponding opening tags).

        Args:
            content: The content to check

        Returns:
            True if orphaned closing tags are found, False otherwise
        """
        # Check for orphaned closing tags (closing tags without opening)
        # For HTML-style tags
        if "</ref>" in content and not ("<ref>" in content or "<ref " in content):
            return True
        if "</nowiki>" in content and "<nowiki>" not in content:
            return True
        if "-->" in content and "<!--" not in content:
            return True

        # For wikilink brackets - check for orphaned closing brackets
        if "]]" in content and "[[" not in content:
            return True

        # For template brackets - check for orphaned closing brackets
        if "}}" in content and "{{" not in content:
            return True

        return False

    @staticmethod
    def _has_unmatched_tags(content: str) -> bool:
        """Check for unmatched opening and closing tags.

        Args:
            content: The content to check

        Returns:
            True if unmatched tags are found, False otherwise
        """
        # Ref tags (including attributes)
        ref_open_simple = content.count("<ref>")
        # For <ref name="..." ...> tags, split by '<ref ' and check if remaining parts have '>'
        ref_open_with_attrs = len([x for x in content.split("<ref ")[1:] if ">" in x])
        ref_open_count = ref_open_simple + ref_open_with_attrs
        ref_close_count = content.count("</ref>")
        if ref_open_count != ref_close_count:
            return True

        # Nowiki tags
        nowiki_open_count = content.count("<nowiki>")
        nowiki_close_count = content.count("</nowiki>")
        if nowiki_open_count != nowiki_close_count:
            return True

        # Comment tags
        comment_open_count = content.count("<!--")
        comment_close_count = content.count("-->")
        if comment_open_count != comment_close_count:
            return True

        # Simple check for wikilinks - unmatched [[ without ]]
        wikilink_open_count = content.count("[[")
        wikilink_close_count = content.count("]]")
        if wikilink_open_count != wikilink_close_count:
            return True

        # Simple check for templates - unmatched {{ without }}
        template_open_count = content.count("{{")
        template_close_count = content.count("}}")
        if template_open_count != template_close_count:
            return True

        return False

    @staticmethod
    def _has_invalid_wikitext_markup(content: str) -> bool:
        """Check if content has invalid wikitext markup using wikitextparser.

        Args:
            content: The content to validate

        Returns:
            True if the content has invalid markup (unclosed tags, orphaned closing tags), False otherwise
        """
        try:
            # Try to parse the content with wikitextparser
            # If parsing fails completely, consider it invalid
            wtp.parse(content)

            # Check for orphaned closing tags
            if ContentClassifier._has_orphaned_closing_tags(content):
                return True

            # Check for unmatched tags
            if ContentClassifier._has_unmatched_tags(content):
                return True

            return False

        except Exception:
            # If wikitextparser fails to parse, consider it invalid
            return True

    @staticmethod
    def should_skip_item(content: str) -> bool:
        """Determine if an item should be skipped from processing.

        Args:
            content: The item content to check

        Returns:
            True if the item should be skipped, False otherwise
        """
        stripped_content = content.strip()
        # Skip empty
        if not stripped_content:
            return True
        # Skip code blocks
        if stripped_content.startswith("```"):
            return True
        # Skip non-prose markers (headers, categories, files, blockquotes, etc.)
        for marker in NON_PROSE_PREFIXES:
            if stripped_content.startswith(marker):
                return True
        # Skip content containing category links
        if contains_categories(stripped_content):
            return True
        # Skip short content
        if len(stripped_content) < MIN_PARAGRAPH_LENGTH:
            return True
        # Skip content with invalid wikitext markup
        if ContentClassifier._has_invalid_wikitext_markup(stripped_content):
            return True
        return False
