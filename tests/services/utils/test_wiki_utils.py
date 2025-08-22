"""Tests for wiki utilities.

This module tests the WikiUtils functionality.
"""

from services.utils.wiki_utils import (
    SectionHeading,
    contains_categories,
    contains_wikilinks,
    extract_lead_content,
    extract_section_content,
    extract_section_headings,
    is_prose_content,
)


class TestIsProse:
    """Test cases for is_prose_content function."""

    def test_prose_content(self):
        """Test detection of prose content."""
        # Valid prose content
        assert is_prose_content("This is a normal paragraph.")
        assert is_prose_content("This paragraph contains a [[wikilink]].")

    def test_non_prose_headers(self):
        """Test that headers are not considered prose."""
        assert not is_prose_content("== Section Header ==")
        assert not is_prose_content("=== Subsection Header ===")

    def test_non_prose_templates(self):
        """Test that templates are not considered prose."""
        assert not is_prose_content("{{Template:Example}}")
        assert not is_prose_content("{{Infobox}}")

    def test_non_prose_categories(self):
        """Test that categories at the start are not considered prose."""
        assert not is_prose_content("[[Category:Example]]")

    def test_non_prose_files(self):
        """Test that file references at the start are not considered prose."""
        assert not is_prose_content("[[File:example.jpg|thumb|Caption]]")

    def test_non_prose_lists(self):
        """Test that list items are not considered prose."""
        # List markers are in NON_PROSE_PREFIXES
        assert not is_prose_content("* Bullet point")
        assert not is_prose_content("# Numbered item")

    def test_non_prose_tables(self):
        """Test that table rows are not considered prose."""
        assert not is_prose_content("| Table cell")
        assert not is_prose_content("! Table header")


class TestExtractSectionHeadings:
    """Test cases for extract_section_headings function."""

    def test_extract_basic_headings(self):
        """Test extraction of basic level 2 section headings."""
        wikitext = """
This is some intro text.

== Overview ==
This is the overview section.

=== History ===
This is a subsection about history.

== Applications ==
This is about applications.
"""
        headings = extract_section_headings(wikitext)
        expected = [
            SectionHeading(text="Lead", level=0),
            SectionHeading(text="Overview", level=2),
            SectionHeading(text="Applications", level=2),
        ]
        assert headings == expected

    def test_extract_nested_headings(self):
        """Test extraction ignores non-level-2 headings."""
        wikitext = """
== Main Section ==
Content here.

=== Subsection ===
More content.

==== Sub-subsection ====
Even more content.

===== Deep section =====
Deep content.

====== Deepest section ======
Deepest content.

== Another Main Section ==
Final content.
"""
        headings = extract_section_headings(wikitext)
        expected = [
            SectionHeading(text="Lead", level=0),
            SectionHeading(text="Main Section", level=2),
            SectionHeading(text="Another Main Section", level=2),
        ]
        assert headings == expected

    def test_extract_headings_with_whitespace(self):
        """Test extraction of level 2 headings with various whitespace patterns."""
        wikitext = """
==   Spaced Heading   ==
===Tight Heading===
== Mixed  Spacing ==
"""
        headings = extract_section_headings(wikitext)
        expected = [
            SectionHeading(text="Lead", level=0),
            SectionHeading(text="Spaced Heading", level=2),
            SectionHeading(text="Mixed  Spacing", level=2),
        ]
        assert headings == expected

    def test_extract_headings_ignores_invalid_patterns(self):
        """Test that invalid heading patterns and non-level-2 headings are ignored."""
        wikitext = """
= Single equals not valid =
== Valid Heading ==
This is not a heading == with equals ==
== Another Valid Heading ==
=== Unmatched heading ===
==== Mismatched heading ===
"""
        headings = extract_section_headings(wikitext)
        expected = [
            SectionHeading(text="Lead", level=0),
            SectionHeading(text="Valid Heading", level=2),
            SectionHeading(text="Another Valid Heading", level=2),
        ]
        assert headings == expected

    def test_extract_headings_empty_text(self):
        """Test extraction from empty text."""
        headings = extract_section_headings("")
        expected = [SectionHeading(text="Lead", level=0)]
        assert headings == expected

    def test_extract_headings_no_headings(self):
        """Test extraction from text with no level 2 headings."""
        wikitext = """
This is just regular text without any headings.
It has multiple paragraphs and some [[links]].
=== Only level 3 heading ===
But no level 2 section headings.
"""
        headings = extract_section_headings(wikitext)
        expected = [SectionHeading(text="Lead", level=0)]
        assert headings == expected


class TestExtractSectionContent:
    """Test cases for extract_section_content function."""

    def test_extract_section_basic(self):
        """Test extraction of a basic section."""
        wikitext = """
This is intro text.

== Overview ==
This is the overview section.
It has multiple lines.

== History ==
This is the history section.
"""
        content = extract_section_content(wikitext, "Overview")
        expected = """== Overview ==
This is the overview section.
It has multiple lines.
"""
        assert content == expected

    def test_extract_section_case_insensitive(self):
        """Test that section extraction is case-insensitive."""
        wikitext = """
== Overview ==
This is the overview section.

== History ==
This is the history section.
"""
        # Test different case variations
        assert extract_section_content(wikitext, "overview") is not None
        assert extract_section_content(wikitext, "OVERVIEW") is not None
        assert extract_section_content(wikitext, "Overview") is not None

    def test_extract_section_with_subsections(self):
        """Test extraction of a level 2 section that contains subsections."""
        wikitext = """
== Main Section ==
Main content here.

=== Subsection ===
Subsection content.

==== Sub-subsection ====
Deep content.

== Another Section ==
Other content.
"""
        content = extract_section_content(wikitext, "Main Section")
        expected = """== Main Section ==
Main content here.

=== Subsection ===
Subsection content.

==== Sub-subsection ====
Deep content.
"""
        assert content == expected

    def test_extract_section_not_found(self):
        """Test extraction when level 2 section doesn't exist."""
        wikitext = """
== Overview ==
This is the overview section.

== History ==
This is the history section.
"""
        content = extract_section_content(wikitext, "Non-existent Section")
        assert content is None

    def test_extract_section_empty_input(self):
        """Test extraction with empty inputs."""
        assert extract_section_content("", "Overview") is None
        assert extract_section_content("Some text", "") is None
        assert extract_section_content("", "") is None

    def test_extract_section_last_section(self):
        """Test extraction of the last level 2 section in a document."""
        wikitext = """
== First Section ==
First content.

== Last Section ==
This is the last section.
It goes to the end of the document.
"""
        content = extract_section_content(wikitext, "Last Section")
        expected = """== Last Section ==
This is the last section.
It goes to the end of the document.
"""
        assert content == expected

    def test_extract_section_nested_levels(self):
        """Test extraction stops at next level 2 heading."""
        wikitext = """
== Section A ==
Content A.

=== Subsection A.1 ===
Subsection content.

== Section B ==
Content B.

=== Subsection B.1 ===
More content.
"""
        content = extract_section_content(wikitext, "Section A")
        expected = """== Section A ==
Content A.

=== Subsection A.1 ===
Subsection content.
"""
        assert content == expected

    def test_extract_subsection(self):
        """Test that subsections (level 3+) are not extractable."""
        wikitext = """
== Main Section ==
Main content.

=== Subsection ===
Subsection content.

=== Another Subsection ===
More content.

== Another Main Section ==
Other content.
"""
        # Should not find the subsection since we only work with level 2
        content = extract_section_content(wikitext, "Subsection")
        assert content is None

    def test_extract_only_level_2_sections(self):
        """Test that only level 2 sections are extractable."""
        wikitext = """
= Level 1 =
Level 1 content.

== Level 2 ==
Level 2 content.

=== Level 3 ===
Level 3 content.

==== Level 4 ====
Level 4 content.
"""
        # Should find level 2 section
        content = extract_section_content(wikitext, "Level 2")
        expected = """== Level 2 ==
Level 2 content.

=== Level 3 ===
Level 3 content.

==== Level 4 ====
Level 4 content.
"""
        assert content == expected

        # Should not find level 1, 3, or 4 sections
        assert extract_section_content(wikitext, "Level 1") is None
        assert extract_section_content(wikitext, "Level 3") is None
        assert extract_section_content(wikitext, "Level 4") is None


class TestContainsWikilinks:
    """Test cases for contains_wikilinks function."""

    def test_contains_wikilinks_true(self):
        """Test detection of wikilinks."""
        assert contains_wikilinks("This has a [[wikilink]].")
        assert contains_wikilinks("Multiple [[link1]] and [[link2]].")

    def test_contains_wikilinks_false(self):
        """Test text without wikilinks."""
        assert not contains_wikilinks("This has no links.")
        assert not contains_wikilinks("This has [external link].")
        assert not contains_wikilinks("[[incomplete")

    def test_contains_wikilinks_edge_cases(self):
        """Test edge cases."""
        assert not contains_wikilinks("")
        # [[]] technically contains [[ and ]], so it should return True
        assert contains_wikilinks("[[]]")


class TestContainsCategories:
    """Test cases for contains_categories function."""

    def test_contains_categories_true(self):
        """Test detection of category links."""
        assert contains_categories("This has [[Category:Example]].")
        assert contains_categories("This has [[:Category:Visible]].")
        assert contains_categories("[[category:lowercase]]")

    def test_contains_categories_false(self):
        """Test text without categories."""
        assert not contains_categories("This has no categories.")
        assert not contains_categories("This has [[Regular Link]].")
        assert not contains_categories("")

    def test_contains_categories_edge_cases(self):
        """Test edge cases for category detection."""
        assert contains_categories("[[Category:Test|Sort key]]")
        assert contains_categories("[[:Category:Hidden category]]")


class TestExtractLeadContent:
    """Test cases for extract_lead_content function."""

    def test_extract_lead_basic(self):
        """Test extraction of basic lead content."""
        wikitext = """This is the lead paragraph.

This is another lead paragraph.

== First Section ==
This is the first section content.

== Second Section ==
This is the second section content.
"""
        content = extract_lead_content(wikitext)
        expected = """This is the lead paragraph.

This is another lead paragraph."""
        assert content == expected

    def test_extract_lead_with_templates(self):
        """Test extraction of lead content with templates."""
        wikitext = """{{Infobox}}
This is the lead paragraph with [[wikilinks]] and {{templates}}.

More lead content here.

== First Section ==
Section content.
"""
        content = extract_lead_content(wikitext)
        expected = """{{Infobox}}
This is the lead paragraph with [[wikilinks]] and {{templates}}.

More lead content here."""
        assert content == expected

    def test_extract_lead_no_sections(self):
        """Test extraction when there are no level 2 sections."""
        wikitext = """This is the entire article.

It has multiple paragraphs.

=== Only level 3 heading ===
But no level 2 headings.
"""
        content = extract_lead_content(wikitext)
        expected = """This is the entire article.

It has multiple paragraphs.

=== Only level 3 heading ===
But no level 2 headings."""
        assert content == expected

    def test_extract_lead_empty_text(self):
        """Test extraction from empty text."""
        content = extract_lead_content("")
        assert content is None

    def test_extract_lead_only_whitespace(self):
        """Test extraction from text with only whitespace."""
        content = extract_lead_content("\n\n  \n\n")
        assert content is None

    def test_extract_lead_first_line_is_section(self):
        """Test when first line is a section heading."""
        wikitext = """== First Section ==
This is the first section content.

== Second Section ==
This is the second section content.
"""
        content = extract_lead_content(wikitext)
        assert content is None

    def test_extract_lead_with_trailing_whitespace(self):
        """Test extraction removes trailing empty lines."""
        wikitext = """This is the lead paragraph.



== First Section ==
Section content.
"""
        content = extract_lead_content(wikitext)
        expected = "This is the lead paragraph."
        assert content == expected


class TestExtractSectionContentWithLead:
    """Test cases for extract_section_content function with lead section support."""

    def test_extract_lead_via_section_content(self):
        """Test extraction of lead section via extract_section_content."""
        wikitext = """This is the lead paragraph.

More lead content.

== First Section ==
Section content.
"""
        content = extract_section_content(wikitext, "Lead")
        expected = """This is the lead paragraph.

More lead content."""
        assert content == expected

    def test_extract_lead_case_insensitive(self):
        """Test that lead extraction is case-insensitive."""
        wikitext = """Lead content here.

== Section ==
Section content.
"""
        # Test different case variations
        assert extract_section_content(wikitext, "lead") is not None
        assert extract_section_content(wikitext, "LEAD") is not None
        assert extract_section_content(wikitext, "Lead") is not None
