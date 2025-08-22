"""Wiki-specific utilities.

This module contains functions specifically for working with wiki text and wiki markup.
"""

import re
from typing import List, NamedTuple, Optional

from services.core.constants import NON_PROSE_PREFIXES


class SectionHeading(NamedTuple):
    """Represents a section heading with its text and level."""

    text: str
    level: int


def is_prose_content(paragraph: str) -> bool:
    """Determines if a paragraph is primarily prose content.

    Content is considered non-prose if it starts with a template, header, etc.

    Args:
        paragraph: The paragraph text to check.

    Returns:
        True if the paragraph is prose content, False otherwise.
    """
    # Empty or whitespace-only strings are not prose
    if not paragraph.strip():
        return False

    # Check for non-prose markers
    for marker in NON_PROSE_PREFIXES:
        if paragraph.startswith(marker):
            return False
    return True


def extract_section_headings(wikitext: str) -> List[SectionHeading]:
    """Extract all level 2 section headings from wikitext content, including lead section.

    Args:
        wikitext: The wikitext content to parse

    Returns:
        List of SectionHeading objects with lead section first, then level 2 headings
    """
    headings = []

    # Always include the lead section as the first option
    headings.append(SectionHeading(text="Lead", level=0))

    # Regex pattern to match level 2 section headings only
    # Matches patterns like == Title ==
    heading_pattern = r"^(={2})\s*([^=]+?)\s*\1\s*$"

    for line in wikitext.split("\n"):
        match = re.match(heading_pattern, line.strip())
        if match:
            heading_text = match.group(2).strip()
            level = 2  # Always level 2

            headings.append(SectionHeading(text=heading_text, level=level))

    return headings


def extract_section_content(wikitext: str, section_title: str) -> Optional[str]:
    """Extract the content of a specific section from wikitext.

    Args:
        wikitext: The wikitext content to parse
        section_title: The title of the section to extract (case-insensitive)
                      Use "Lead" to extract the lead section

    Returns:
        The content of the specified section, or None if not found
    """
    if not wikitext.strip() or not section_title.strip():
        return None

    # Handle lead section extraction
    if section_title.lower() == "lead":
        return extract_lead_content(wikitext)

    lines = wikitext.split("\n")
    section_found = False
    section_content = []
    heading_pattern = r"^(={2})\s*([^=]+?)\s*\1\s*$"  # Only match level 2 headings

    for line in lines:
        line_stripped = line.strip()
        match = re.match(heading_pattern, line_stripped)

        if match:
            heading_text = match.group(2).strip()

            # Check if this is the section we're looking for (case-insensitive)
            if heading_text.lower() == section_title.lower():
                section_found = True
                section_content.append(line)  # Include the heading itself
                continue

            # If we found our section and this is another level 2 heading, stop
            elif section_found:
                break

        # If we're in the target section, collect all content
        if section_found:
            section_content.append(line)

    if section_found and section_content:
        return "\n".join(section_content)

    return None


def extract_lead_content(wikitext: str) -> Optional[str]:
    """Extract the lead section content from wikitext.

    The lead section is everything before the first level 2 heading (== Section ==).

    Args:
        wikitext: The wikitext content to parse

    Returns:
        The lead section content, or None if no content found
    """
    if not wikitext.strip():
        return None

    lines = wikitext.split("\n")
    lead_content = []
    heading_pattern = r"^(={2})\s*([^=]+?)\s*\1\s*$"  # Match level 2 headings

    for line in lines:
        line_stripped = line.strip()
        match = re.match(heading_pattern, line_stripped)

        # Stop at the first level 2 heading
        if match:
            break

        lead_content.append(line)

    if lead_content:
        # Remove trailing empty lines
        while lead_content and not lead_content[-1].strip():
            lead_content.pop()

        if lead_content:
            return "\n".join(lead_content)

    return None


def contains_wikilinks(text: str) -> bool:
    """Checks if the text likely contains wikilinks.

    Args:
        text: The text to check.

    Returns:
        True if the text appears to contain wikilinks.
    """
    return "[[" in text and "]]" in text


def contains_categories(text: str) -> bool:
    """Checks if the text contains wikitext category links.

    Detects both regular categories [[Category:Name]] and visible category links
    [[:Category:Name]].

    Args:
        text: The text to check.

    Returns:
        True if the text contains category links.
    """
    # Pattern to match both [[Category:...]] and [[:Category:...]]
    category_pattern = r"\[\[:?Category:[^\]]+\]\]"
    return bool(re.search(category_pattern, text, re.IGNORECASE))
