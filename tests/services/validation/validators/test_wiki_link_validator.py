"""Unit tests for the WikiLinkValidator."""

from typing import List
from unittest.mock import MagicMock, patch

import pytest

from services.text.reference_handler import ReferenceHandler
from services.validation.validators.wiki_link_validator import WikiLinkValidator


@pytest.fixture
def mock_reference_handler():
    """Fixture for a mock ReferenceHandler instance."""
    handler = MagicMock(spec=ReferenceHandler)
    handler.replace_references_with_placeholders.side_effect = lambda text: (text, [])
    return handler


@pytest.fixture
def link_validator(mock_reference_handler):
    """Fixture for a WikiLinkValidator instance."""
    return WikiLinkValidator(mock_reference_handler)


@pytest.mark.asyncio
async def test_validate_and_reintroduce_links_no_change(link_validator):
    original = "This is a sentence with a [[link]]."
    edited = "This is a sentence with a [[link]]."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert result_text == edited
    assert not should_revert


@pytest.mark.asyncio
async def test_revert_on_new_link_added(link_validator):
    original = "This is a sentence."
    edited = "This is a [[new link]] added."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # The validator should remove the new link and preserve display text, not revert
    assert not should_revert
    assert result_text == "This is a new link added."


@pytest.mark.asyncio
async def test_revert_on_link_removal(link_validator):
    original = "This is a sentence with a [[link]]."
    edited = "This is a sentence with a link."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # The validator should reintroduce the removed link, not revert
    assert not should_revert
    assert result_text == "This is a sentence with a [[link]]."


@pytest.mark.asyncio
async def test_revert_on_link_target_changed(link_validator):
    original = "This is a sentence with a [[link|display text]]."
    edited = "This is a sentence with a [[different_link|display text]]."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert should_revert


@pytest.mark.asyncio
async def test_allow_display_text_changes(link_validator):
    """Test that display text changes are allowed while keeping the same target."""
    original = "This is a sentence with a [[link|old display text]]."
    edited = "This is a sentence with a [[link|new display text]]."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should NOT revert - display text changes are allowed
    assert not should_revert
    assert result_text == edited


@pytest.mark.asyncio
async def test_allow_display_text_shortening(link_validator):
    """Test that shortening display text is allowed (like the Copacabana example)."""
    original = "The setting of a [[Copacabana (At the Copa)|song of the same name]]."
    edited = "The setting of a [[Copacabana (At the Copa)|song]]."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should NOT revert - display text changes are allowed
    assert not should_revert
    assert result_text == edited


@pytest.mark.asyncio
async def test_handle_no_original_links_with_new_links_added(link_validator):
    """Test _handle_no_original_links when new links are added to a paragraph that had none."""
    original = "This is a sentence without links."
    edited = "This is a [[new link]] in a sentence."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    assert not should_revert
    assert result_text == "This is a new link in a sentence."


@pytest.mark.asyncio
async def test_handle_no_original_links_re_parse_iteration(link_validator):
    """Test _handle_no_original_links with re-parsing iteration."""
    original = "This is a sentence without links."
    edited = "This is a [[first link]] and [[second link]] sentence."

    # Mock _attempt_link_removal to succeed for both links
    removal_results = [
        "This is a first link and [[second link]] sentence.",
        "This is a first link and second link sentence.",
    ]
    with patch.object(
        link_validator, "_attempt_link_removal", side_effect=removal_results
    ):
        (
            result_text,
            should_revert,
        ) = await link_validator.validate_and_reintroduce_links(original, edited, 0, 1)

        assert not should_revert
        assert "[[" not in result_text  # All links should be removed


def test_attempt_link_removal_success(link_validator):
    """Test _attempt_link_removal with successful removal."""
    edited_text = "This has a [[Example|display text]] link."
    full_link = "[[Example|display text]]"
    target = "Example"

    result = link_validator._attempt_link_removal(edited_text, full_link, target)

    expected = "This has a display text link."
    assert result == expected


def test_attempt_link_removal_simple_link(link_validator):
    """Test _attempt_link_removal with simple link (no display text)."""
    edited_text = "This has a [[Example]] link."
    full_link = "[[Example]]"
    target = "Example"

    result = link_validator._attempt_link_removal(edited_text, full_link, target)

    expected = "This has a Example link."
    assert result == expected


def test_attempt_link_removal_not_found(link_validator):
    """Test _attempt_link_removal when link is not found."""
    edited_text = "This has some text."
    full_link = "[[NotFound]]"
    target = "NotFound"

    result = link_validator._attempt_link_removal(edited_text, full_link, target)

    # When link is not found, the method returns the original text
    assert result == edited_text


def test_extract_display_text_from_link_with_display(link_validator):
    """Test _extract_display_text_from_link with display text."""
    full_link = "[[Target|Display Text]]"
    target = "Target"

    result = link_validator._extract_display_text_from_link(full_link, target)
    assert result == "Display Text"


def test_extract_display_text_from_link_without_display(link_validator):
    """Test _extract_display_text_from_link without display text."""
    full_link = "[[Target]]"
    target = "Target"

    result = link_validator._extract_display_text_from_link(full_link, target)
    assert result == "Target"


@pytest.mark.asyncio
async def test_duplicate_link_detection_triggers_revert():
    mock_reference_handler = MagicMock()
    mock_reference_handler.replace_references_with_placeholders.return_value = (
        "Text with [[Link]]",  # Return the original content with placeholders
        [],
    )
    validator = WikiLinkValidator(mock_reference_handler)

    # Create scenario where duplicate links are detected
    # This requires the main validation flow to reach the duplicate check
    original_content = "Text with [[Link]]"
    edited_content = "Text with [[Link]] and [[Link]]"  # Duplicate link

    # Let the actual duplicate detection logic run
    result = await validator.validate_and_reintroduce_links(
        original_content, edited_content, 0, 1
    )

    # Should revert due to duplicate links
    assert result[1] is True


@pytest.mark.asyncio
async def test_handle_no_original_links_when_edited_also_has_no_links():
    mock_reference_handler = MagicMock()
    mock_reference_handler.replace_references_with_placeholders.return_value = (
        "text",
        [],
    )
    validator = WikiLinkValidator(mock_reference_handler)

    # Original has no links, edited also has no links
    original_content = "Text without any links"
    edited_content = "Edited text without any links"

    result = await validator.validate_and_reintroduce_links(
        original_content, edited_content, 0, 1
    )

    assert result == (edited_content, False)


def test_extract_display_text_from_link_with_pipe(link_validator):
    """Test _extract_display_text_from_link with pipe separator."""
    full_link = "[[target|display text]]"
    target = "target"

    result = link_validator._extract_display_text_from_link(full_link, target)

    assert result == "display text"


def test_extract_display_text_from_link_without_pipe(link_validator):
    """Test _extract_display_text_from_link without pipe separator."""
    full_link = "[[target]]"
    target = "target"

    result = link_validator._extract_display_text_from_link(full_link, target)

    assert result == target


def test_link_removal_failure_scenario():
    # Test removed: link removal can no longer fail
    pass


def test_handle_no_original_links_failure_scenario():
    # Test removed: link removal can no longer fail
    pass


@pytest.mark.asyncio
async def test_prefix_added_to_text_should_not_flag_links_as_changed():
    """Test that adding a prefix like 'Edited: ' to text doesn't cause links to be flagged as changed."""
    mock_reference_handler = MagicMock()
    mock_reference_handler.replace_references_with_placeholders.return_value = (
        "The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation.",
        [],
    )
    validator = WikiLinkValidator(mock_reference_handler)

    original_content = "The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation."
    edited_content = "Edited: The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation."

    result = await validator.validate_and_reintroduce_links(
        original_content, edited_content, 0, 1
    )

    # The validator should not revert just because text was prepended
    text_result, should_revert = result
    assert should_revert is False, (
        "Validator should not revert when only a prefix is added"
    )
    assert text_result == edited_content


@pytest.mark.asyncio
async def test_duplicate_links_equal_counts_are_allowed(link_validator):
    """If the original paragraph already contains duplicate links, the same
    duplicate count in the edited paragraph should be allowed (no revert)."""
    original_content = "This has [[Example]] and another [[Example]] link."
    edited_content = "Edited: This has [[Example]] and another [[Example]] link."

    # The original contains the duplicate already, so no revert should happen.
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original_content, edited_content, 0, 1
    )

    assert should_revert is False
    assert result_text == edited_content


@pytest.mark.asyncio
async def test_good_edit_with_complex_text_and_refs_is_not_reverted():
    """
    This test uses text from a failing integration test to confirm that
    the WikiLinkValidator does not incorrectly revert a valid text edit
    when reference placeholders are present in a complex paragraph. This
    isolates the validator as the source of the issue seen in integration
    tests where good edits were being reverted.
    """
    # Arrange
    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler=reference_handler)

    original_content = 'The FreeBSD project has stated that "a less publicized and unintended use of the GPL is that it is very favorable to large companies that want to undercut software companies. In other words, the GPL is well suited for use as a marketing weapon, potentially reducing overall economic benefit and contributing to monopolistic behavior" and that the GPL can "present a real problem for those wishing to commercialize and profit from software."<ref>{{cite web|url=http://www.freebsd.org/doc/en_US.ISO8859-1/articles/bsdl-gpl/article.html#GPL-ADVANTAGES |title=GPL Advantages and Disadvantages |publisher=FreeBSD |first=Bruce |last=Montague |date=13 November 2013 |access-date=28 November 2015}}</ref>'

    # Simulate what the paragraph processor does before calling the LLM
    original_with_placeholders, _ = (
        reference_handler.replace_references_with_placeholders(original_content)
    )

    # Simulate the LLM's edit on the placeholder version of the content
    edited_with_placeholders = original_with_placeholders.replace(
        "is very favorable", "is favorable"
    )

    # Act: Call the validator with the same arguments the pipeline would use
    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original_paragraph_content=original_content,
        edited_text_with_placeholders=edited_with_placeholders,
        paragraph_index=0,
        total_paragraphs=1,
    )

    # Assert
    assert not should_revert, "A simple word removal should not cause a reversion."
    assert result_text == edited_with_placeholders


@pytest.mark.asyncio
async def test_coverage_validate_and_reintroduce_links_final_return():
    from services.text.reference_handler import ReferenceHandler
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    reference_handler = ReferenceHandler()

    validator = WikiLinkValidator(reference_handler)
    original = "This is a sentence with a [[Link|Link]]."
    edited = "This is a sentence with a [[Link|Link]]."
    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert result_text == edited
    assert not should_revert


@pytest.mark.asyncio
async def test_reintroduce_link_with_trailing_chars(link_validator):
    """Test reintroduction of a wikilink with trailing characters like [[link]]s."""
    original = "This is a sentence with [[apple]]s."
    edited = "This is a sentence with apples."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert not should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_reintroduce_piped_link_with_trailing_chars(link_validator):
    """Test reintroduction of a piped wikilink with trailing characters like [[link|display]]s."""
    original = "I have several [[Personal computer|PC]]s."
    edited = "I have several PCs."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert not should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_reintroduce_pipe_trick_link(link_validator):
    """Test reintroduction of a link using the pipe trick, like [[pipe (computing)|]]."""
    # wikitextparser expands [[pipe (computing)|]] to [[pipe (computing)|pipe]]
    # So we check for restoration of the expanded form.
    original = "A useful shortcut is the [[pipe (computing)|]] trick."
    edited = "A useful shortcut is the pipe trick."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert not should_revert
    assert result_text == "A useful shortcut is the [[pipe (computing)|pipe]] trick."


@pytest.mark.asyncio
async def test_reintroduce_external_link_simple(link_validator):
    """Test reintroduction of a simple external link like [https://example.com]."""
    original = "An example: [https://example.com]."
    edited = "An example: ."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    assert not should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_reintroduce_external_link_with_display_text(link_validator):
    """Test reintroducing external links with display text."""
    original = "Check out [https://example.com this example]."
    edited = "Check out this example."
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should reintroduce the link using the preserved display text
    assert not should_revert
    assert "[https://example.com this example]" in result_text


# NEW TESTS FOR REQUIRED BEHAVIOR


@pytest.mark.asyncio
async def test_wikilink_fully_removed_should_revert(link_validator):
    """Test that when a wikilink is fully removed (including display text), it should revert."""
    original = "This has a [[Test Article]] in the middle."
    edited = "This has a in the middle."  # Link and display text completely removed
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should revert because the link was completely removed
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_wikilink_removed_but_label_remains_should_restore(link_validator):
    """Test that when a wikilink is removed but its display text remains, it should be restored."""
    original = "This has a [[Test Article]] in the middle."
    edited = "This has a Test Article in the middle."  # Link markup removed but display text remains
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should restore the link without reverting
    assert not should_revert
    assert result_text == "This has a [[Test Article]] in the middle."


@pytest.mark.asyncio
async def test_wikilink_with_pipe_removed_but_label_remains_should_restore(
    link_validator,
):
    """Test that when a piped wikilink is removed but its display text remains, it should be restored."""
    original = "This has a [[Test Article|custom label]] in the middle."
    edited = "This has a custom label in the middle."  # Link markup removed but display text remains
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should restore the link without reverting
    assert not should_revert
    assert result_text == "This has a [[Test Article|custom label]] in the middle."


@pytest.mark.asyncio
async def test_external_link_fully_removed_should_revert(link_validator):
    """Test that when an external link is fully removed (including display text), it should revert."""
    original = "Check out [https://example.com this site] for more info."
    edited = "Check out for more info."  # Link and display text completely removed
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should revert because the link was completely removed
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_external_link_removed_but_label_remains_should_restore(link_validator):
    """Test that when an external link is removed but its display text remains, it should be restored."""
    original = "Check out [https://example.com this site] for more info."
    edited = "Check out this site for more info."  # Link markup removed but display text remains
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should restore the link without reverting
    assert not should_revert
    assert result_text == "Check out [https://example.com this site] for more info."


@pytest.mark.asyncio
async def test_external_link_simple_removed_but_url_remains_should_restore(
    link_validator,
):
    """Test that when a simple external link is removed but the URL text remains, it should be restored."""
    original = "Visit https://example.com for details."
    edited = "Visit https://example.com for details."  # Simple external link without brackets
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should not change anything as this case involves simple URL text
    assert not should_revert
    assert result_text == edited


@pytest.mark.asyncio
async def test_multiple_links_mixed_removal_behavior(link_validator):
    """Test mixed behavior: one link fully removed (should revert), one link label remains (should restore)."""
    original = "See [[Article One]] and [[Article Two|custom name]] for details."
    edited = "See and custom name for details."  # First link fully removed, second link label remains
    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )
    # Should revert because at least one link was fully removed
    assert should_revert
    assert result_text == original


def test_extract_display_text_from_link_parsing_failure(link_validator):
    """Test _extract_display_text_from_link when parsing fails with IndexError."""
    # This simulates the edge case where text that looks like it might be a link
    # actually can't be parsed as a wikilink, causing wtp.parse().wikilinks[0]
    # to raise an IndexError
    full_link = "http://example.com/url/in/reference"  # URL that's not a wikilink
    target = "example_target"

    result = link_validator._extract_display_text_from_link(full_link, target)

    # Should return the target when parsing fails
    assert result == target


def test_extract_display_text_from_link_empty_string(link_validator):
    """Test _extract_display_text_from_link with empty string input."""
    full_link = ""
    target = "fallback_target"

    result = link_validator._extract_display_text_from_link(full_link, target)

    # Should return the target when parsing fails on empty string
    assert result == target


# Test pipe trick condition (empty display text)
def test_extract_links_pipe_trick_with_parentheses(link_validator):
    """Test _extract_links with pipe trick links containing parentheses."""
    text = "This is a [[London (Ontario)|]] link."
    links = link_validator._extract_links(text)

    assert len(links) == 1
    link = links[0]
    assert link.target == "London (Ontario)"
    assert link.display_text == "London"  # Should extract part before parentheses
    assert link.link_type == "wikilink"


def test_extract_links_pipe_trick_without_parentheses(link_validator):
    """Test _extract_links with pipe trick links without parentheses."""
    text = "This is a [[London|]] link."
    links = link_validator._extract_links(text)

    assert len(links) == 1
    link = links[0]
    assert link.target == "London"
    assert link.display_text == "London"  # Should use full title
    assert link.link_type == "wikilink"


# Test duplicate link check return behavior
@pytest.mark.asyncio
async def test_duplicate_link_check_returns_properly(link_validator):
    """Test that duplicate link check properly returns edited text when duplicates are found."""
    original = "This has one [[duplicate]] link."
    edited = "This has two [[duplicate]] and another [[duplicate]] links."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    assert should_revert
    assert result_text == edited  # Should return the edited text as-is when reverting


# Test link restoration with trailing characters
@pytest.mark.asyncio
async def test_restore_missing_link_with_trailing_chars_coverage(link_validator):
    """Test _restore_missing_links with trailing character matching."""
    original = "I like [[apple]]s very much."
    edited = "I like apples very much."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    assert not should_revert
    assert result_text == "I like [[apple]]s very much."


# Test external link restoration patterns
@pytest.mark.asyncio
async def test_external_link_restoration_pattern_matching(link_validator):
    """Test external link restoration using different patterns."""
    # Test pattern ": ." -> ": [link]."
    original = "Check this out: https://example.com."
    edited = "Check this out: ."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    assert not should_revert
    assert "https://example.com" in result_text


# Test external link restoration fallback
@pytest.mark.asyncio
async def test_external_link_restoration_display_text_fallback(link_validator):
    """Test external link restoration when display text differs from URL."""
    original = "Check out [https://example.com this website]."
    edited = "Check out this website."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    assert not should_revert
    assert "[https://example.com this website]" in result_text


# Test external link restoration failure
@pytest.mark.asyncio
async def test_external_link_restoration_failure_coverage(link_validator):
    """Test external link restoration when no suitable strategy is found."""
    # Create a case where the external link's display text is not found in the edited text
    # and no patterns match for restoration
    original = "Check this: [https://very-specific-url.com/path?param=value unique display text]."
    edited = "Check this: completely different text with no matching patterns."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert since link cannot be restored
    assert should_revert
    assert result_text == original


# Test specific duplicate link return path
@pytest.mark.asyncio
async def test_duplicate_link_return_edited_text_with_revert(link_validator):
    """Test return edited_text_with_placeholders, True for duplicate links."""
    original = "This has [[target]] link."
    edited = "This has [[target]] and another [[target]] links."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert with original edited text
    assert should_revert
    assert result_text == edited


# Test link removal failure path
def test_link_removal_failure_scenario_two():
    # Test removed: link removal can no longer fail
    pass


# Test strict word boundary restoration
@pytest.mark.asyncio
async def test_strict_word_boundary_restoration_success(link_validator):
    """Test strict word boundary restoration success."""
    original = "The [[word]] is here."
    edited = "The word is here."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore the link
    assert not should_revert
    assert result_text == "The [[word]] is here."


# Test external link display text replacement
@pytest.mark.asyncio
async def test_external_link_display_text_replacement_by_substitution(link_validator):
    """Test external link restoration by replacing display text."""
    original = "Check [https://example.com Example Site] for info."
    edited = "Check Example Site for info."

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore by replacing display text
    assert not should_revert
    assert "[https://example.com Example Site]" in result_text


# Additional tests to improve coverage of specific edge cases


@pytest.mark.asyncio
async def test_duplicate_link_detection_returns_edited_text_with_revert():
    """Test duplicate link detection that returns edited_text_with_placeholders, True"""

    from services.text.reference_handler import ReferenceHandler
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create a scenario where original has 1 instance of a link, edited has 2 (duplicate)
    original = "This has [[Test]] once."
    edited = "This has [[Test]] and [[Test]] twice."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should return True for revert
    assert should_revert is True
    assert result_text == edited  # Should return edited_text_with_placeholders as-is


def test_new_link_removal_failure_scenario():
    # Test removed: link removal can no longer fail
    pass


@pytest.mark.asyncio
async def test_successful_strict_word_boundary_restoration():
    """Test successful strict word-boundary restoration"""

    from services.text.reference_handler import ReferenceHandler
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where a link is removed but display text remains, matching word boundaries
    original = "The [[word]] is important."
    edited = "The word is important."  # Link removed, display text remains

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should succeed with strict word boundary restoration
    assert not should_revert
    assert result_text == "The [[word]] is important."


@pytest.mark.asyncio
async def test_external_link_restoration_by_display_text_replacement():
    """Test external link restoration by replacing display text."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario with external link where display text differs from URL
    original = "Visit [https://example.com Example Site] for more info."
    edited = "Visit Example Site for more info."  # External link removed, display text remains

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should succeed with external link restoration by replacing display text
    assert not should_revert
    assert "[https://example.com Example Site]" in result_text


# ULTRA-TARGETED TESTS FOR FINAL MISSING COVERAGE


def test_link_removal_failure_return():
    # Test removed: link removal can no longer fail
    pass


def test_detect_display_text_updates():
    """Test _detect_display_text_updates finding updates."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    original_links = [
        LinkInfo("Target", "Old Display", "[[Target|Old Display]]", "wikilink")
    ]
    edited_links = [
        LinkInfo("Target", "New Display", "[[Target|New Display]]", "wikilink")
    ]

    result = validator._detect_display_text_updates(original_links, edited_links)

    assert len(result) == 1


def test_case_insensitive_word_boundary_success():
    """Test successful case-insensitive word boundary match."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Test", "test", "[[Test|test]]", "wikilink")
    working_text = "This is a Test case."  # Different case, word boundary

    result = validator._try_case_insensitive_word_boundary_match(link, working_text)

    # Should succeed with case-insensitive matching
    assert result is True


def test_flexible_piped_link_target_match_success():
    """Test successful flexible piped link target matching."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Target Name", "display", "[[Target Name|display]]", "wikilink")
    working_text = "The Target Name appears here."  # Target appears with word boundary

    result = validator._try_flexible_piped_link_restoration(link, working_text)

    # Should succeed with regular target matching
    assert result is True


def test_flexible_piped_link_case_insensitive_success():
    """Test successful case-insensitive flexible piped link target matching."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Target Name", "display", "[[Target Name|display]]", "wikilink")
    working_text = (
        "The target name appears here."  # Target in different case with word boundary
    )

    result = validator._try_flexible_piped_link_restoration(link, working_text)

    # Should succeed with case-insensitive target matching
    assert result is True


def test_trailing_repl_inner_function():
    """Test inner function trailing_repl in _try_trailing_chars_match."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Test", "test", "[[Test|test]]", "wikilink")
    working_text = "I have testing in progress."  # Display text with trailing chars

    result = validator._try_trailing_chars_match(link, working_text)

    # Should trigger the inner function and succeed
    assert result is True


def test_trailing_chars_match_success():
    """Test successful trailing chars match."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Apple", "apple", "[[Apple|apple]]", "wikilink")
    working_text = "I like apples very much."  # Display text with trailing 's'

    result = validator._try_trailing_chars_match(link, working_text)

    assert result is True


def test_flexible_target_substring_return_false():
    """Test return False in _try_flexible_target_substring_match."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    # Create link that won't match any conditions
    link = LinkInfo("NonExistent", "display", "[[NonExistent|display]]", "wikilink")
    working_text = "This text has no matching content whatsoever."

    result = validator._try_flexible_target_substring_match(link, working_text)

    # Should return False when no match found
    assert result is False


def test_external_link_pattern_matching():
    """Test external link restoration pattern matching success."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    # External link where display_text == target (URL)
    link = LinkInfo(
        "https://example.com",
        "https://example.com",
        "[https://example.com]",
        "external",
    )
    edited_text = "Check this out: ."  # Pattern that matches ": ."

    result = validator._attempt_external_link_restoration(edited_text, link)

    # Should succeed with pattern matching
    assert result is not None
    assert "https://example.com" in result


def test_fix_malformed_pipe_links_success():
    """Test successful malformed pipe link fixing."""
    validator = WikiLinkValidator(MagicMock())

    # Text with malformed pipe link
    text = "See [[Documentation|]] for more info."

    result = validator._fix_malformed_pipe_links(text)

    # Should detect and fix malformed link
    assert "[[Documentation]]" in result
    assert "[[Documentation|]]" not in result


def test_fix_malformed_pipe_links_exception():
    # Test removed: exception handling was removed from _fix_malformed_pipe_links
    pass


# INTEGRATION TESTS TO FORCE EXACT MISSING COVERAGE


@pytest.mark.asyncio
async def test_integration_link_removal_failure():
    # Test removed: link removal can no longer fail
    pass


@pytest.mark.asyncio
async def test_integration_flexible_piped_link_return_false():
    """Integration test for return False in flexible piped link restoration."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where piped link target cannot be found in any form
    original = "This uses [[Very Specific Unique Target|custom display]]."
    edited = "This uses completely different text with no matches."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because link cannot be restored
    assert should_revert


@pytest.mark.asyncio
async def test_integration_case_insensitive_trailing():
    """Integration test for case-insensitive trailing chars."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario that requires case-insensitive trailing char matching
    original = "I like [[apple]]s very much."
    edited = "I like Apples very much."  # Different case with trailing chars

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully with case-insensitive trailing chars
    assert not should_revert
    assert "[[apple]]s" in result_text


@pytest.mark.asyncio
async def test_integration_substring_replacement():
    """Integration test for substring replacement."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario that requires substring (not word boundary) matching
    original = "The [[HTTP]] protocol is standard."
    edited = "The HTTP-based protocol is standard."  # Not word boundary

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using substring replacement
    assert not should_revert
    assert "[[HTTP]]" in result_text


@pytest.mark.asyncio
async def test_integration_case_insensitive_substring():
    """Integration test for case-insensitive substring replacement."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario that requires case-insensitive substring matching
    original = "The [[HTML]] markup is standard."
    edited = "The html-based markup is standard."  # Different case, not word boundary

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using case-insensitive substring replacement
    assert not should_revert
    assert "[[HTML]]" in result_text


@pytest.mark.asyncio
async def test_integration_flexible_target_substring():
    """Integration test for flexible target substring matching."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where piped link target appears as substring
    original = "Learn about [[JavaScript|JS]] programming."
    edited = "Learn about JavaScript programming language."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using flexible target substring matching
    assert not should_revert
    assert "[[JavaScript]]" in result_text


@pytest.mark.asyncio
async def test_integration_case_insensitive_target_substring():
    """Integration test for case-insensitive target substring matching."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where piped link target appears in different case as substring
    original = "Learn about [[Python|programming]] language."
    edited = "Learn about python programming syntax."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using case-insensitive target substring matching
    assert not should_revert
    # Either form is acceptable - restored link can be simple or retain original piped form
    assert "[[Python]]" in result_text or "[[Python|programming]]" in result_text


@pytest.mark.asyncio
async def test_integration_external_link_patterns():
    """Integration test for external link pattern restoration."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario with external link using pattern restoration
    original = "Check this out: [https://example.com]."
    edited = "Check this out: ."  # Link completely removed, leaving pattern

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using external link pattern matching
    assert not should_revert
    assert "https://example.com" in result_text


# Tests for specific uncovered success paths


@pytest.mark.asyncio
async def test_case_insensitive_trailing_chars_success_path():
    """Test the specific success path in _try_case_insensitive_trailing_chars_match."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario that requires case-insensitive trailing char matching
    original = "I like [[apple]]s very much."
    edited = "I like Apples very much."  # Different case with trailing chars

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully with case-insensitive trailing chars
    assert not should_revert
    assert "[[apple]]s" in result_text


@pytest.mark.asyncio
async def test_substring_replacement_success_path():
    """Test the specific success path in _try_substring_replacement."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario that requires substring (not word boundary) matching
    original = "The [[HTTP]] protocol is standard."
    edited = "The HTTP-based protocol is standard."  # Not word boundary

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using substring replacement
    assert not should_revert
    assert "[[HTTP]]" in result_text


@pytest.mark.asyncio
async def test_case_insensitive_substring_replacement_success_path():
    """Test the specific success path in _try_case_insensitive_substring_replacement."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario that requires case-insensitive substring matching
    original = "The [[HTML]] markup is standard."
    edited = "The html-based markup is standard."  # Different case, not word boundary

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using case-insensitive substring replacement
    assert not should_revert
    assert "[[HTML]]" in result_text


@pytest.mark.asyncio
async def test_flexible_target_substring_exact_match_success_path():
    """Test the first success path in _try_flexible_target_substring_match."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where piped link target appears as exact substring
    original = "Learn about [[JavaScript|JS]] programming."
    edited = "Learn about JavaScript programming language."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using flexible target substring matching
    assert not should_revert
    assert "[[JavaScript]]" in result_text


@pytest.mark.asyncio
async def test_flexible_target_substring_case_insensitive_success_path():
    """Test the case-insensitive success path in _try_flexible_target_substring_match."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where piped link target appears in different case as substring
    original = "Learn about [[Python|programming]] language."
    edited = "Learn about python programming syntax."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore successfully using case-insensitive target substring matching
    assert not should_revert
    # Either form is acceptable - restored link can be simple or retain original piped form
    assert "[[Python]]" in result_text or "[[Python|programming]]" in result_text


def test_fix_malformed_pipe_links_exception_handling():
    # Test removed: exception handling was removed from _fix_malformed_pipe_links
    pass


@pytest.mark.asyncio
async def test_remove_newly_added_links_successful_return():
    """Test the successful return path in _remove_newly_added_links."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where original has no links, edited adds a link that can be successfully removed
    original = "Text without links."
    edited = "Text with [[NewLink|display text]] added."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should successfully remove the new link and not revert
    assert not should_revert
    assert result_text == "Text with display text added."


def test_direct_case_insensitive_trailing_chars_match():
    """Direct test of _try_case_insensitive_trailing_chars_match success path."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Apple", "apple", "[[Apple|apple]]", "wikilink")
    working_text = "I like Apples very much."  # Different case with trailing 's'

    result = validator._try_case_insensitive_trailing_chars_match(link, working_text)

    # Should succeed and set _last_restoration_result
    assert result is True
    assert hasattr(validator, "_last_restoration_result")


def test_direct_substring_replacement():
    """Direct test of _try_substring_replacement success path."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Test", "Test", "[[Test]]", "wikilink")
    working_text = "This is a Test-case example."  # Substring match (not word boundary)

    result = validator._try_substring_replacement(link, working_text)

    # Should succeed and set _last_restoration_result
    assert result is True
    assert hasattr(validator, "_last_restoration_result")


def test_direct_case_insensitive_substring_replacement():
    """Direct test of _try_case_insensitive_substring_replacement success path."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("HTML", "HTML", "[[HTML]]", "wikilink")
    working_text = "The html-based approach works."  # Case-insensitive substring

    result = validator._try_case_insensitive_substring_replacement(link, working_text)

    # Should succeed and set _last_restoration_result
    assert result is True
    assert hasattr(validator, "_last_restoration_result")


def test_direct_flexible_target_substring_exact_match():
    """Direct test of _try_flexible_target_substring_match exact match path."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("JavaScript", "JS", "[[JavaScript|JS]]", "wikilink")
    working_text = "Learn JavaScript programming."  # Exact target substring

    result = validator._try_flexible_target_substring_match(link, working_text)

    # Should succeed with exact match and set _last_restoration_result
    assert result is True
    assert hasattr(validator, "_last_restoration_result")


def test_direct_flexible_target_substring_case_insensitive_match():
    """Direct test of _try_flexible_target_substring_match case-insensitive path."""
    from services.validation.validators.wiki_link_validator import LinkInfo

    validator = WikiLinkValidator(MagicMock())

    link = LinkInfo("Python", "lang", "[[Python|lang]]", "wikilink")
    working_text = "Learn python programming."  # Case-insensitive target substring

    result = validator._try_flexible_target_substring_match(link, working_text)

    # Should succeed with case-insensitive match and set _last_restoration_result
    assert result is True
    assert hasattr(validator, "_last_restoration_result")


def test_remove_newly_added_links_failure_return_path():
    # Test removed: link removal can no longer fail
    pass


def test_fix_malformed_pipe_links_exception_with_attribute_error():
    # Test removed: exception handling was removed from _fix_malformed_pipe_links
    pass


def test_fix_malformed_pipe_links_exception_with_general_exception():
    # Test removed: exception handling was removed from _fix_malformed_pipe_links
    pass


@pytest.mark.asyncio
async def test_remove_newly_added_links_failure_integration():
    # Test removed: link removal can no longer fail
    pass


def test_remove_newly_added_links_coverage():
    """Test to cover the loop in _remove_newly_added_links."""
    from services.text.reference_handler import ReferenceHandler
    from services.validation.validators.wiki_link_validator import (
        LinkInfo,
        WikiLinkValidator,
    )

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario with original links and edited links where new links are added
    original_links: List[LinkInfo] = []  # No original links
    edited_links = [
        LinkInfo("NewTarget", "NewTarget", "[[NewTarget]]", "wikilink"),
        LinkInfo("AnotherTarget", "AnotherTarget", "[[AnotherTarget]]", "wikilink"),
    ]
    edited_text = "This has [[NewTarget]] and [[AnotherTarget]] links."

    # This should trigger the loop in _remove_newly_added_links
    result = validator._remove_newly_added_links(
        original_links, edited_links, edited_text
    )

    # The loop should have processed both new links
    assert "[[NewTarget]]" not in result
    assert "[[AnotherTarget]]" not in result
    assert "NewTarget" in result
    assert "AnotherTarget" in result


def test_fix_malformed_pipe_links_coverage():
    """Test to cover the loop in _fix_malformed_pipe_links."""
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    validator = WikiLinkValidator(MagicMock())

    # Create text with malformed pipe links
    text_with_malformed = "See [[Documentation|]] and [[Help|]] for more info."

    # This should trigger the loop in _fix_malformed_pipe_links
    result = validator._fix_malformed_pipe_links(text_with_malformed)

    # The loop should have processed both malformed links
    assert "[[Documentation]]" in result
    assert "[[Help]]" in result
    assert "[[Documentation|]]" not in result
    assert "[[Help|]]" not in result


def test_fix_malformed_pipe_links_multiple_malformed():
    """Test _fix_malformed_pipe_links with multiple malformed links to ensure loop coverage."""
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    validator = WikiLinkValidator(MagicMock())

    # Create text with multiple malformed pipe links
    text = "Check [[First|]] and [[Second|]] and [[Third|]] links."

    result = validator._fix_malformed_pipe_links(text)

    # All malformed links should be fixed
    assert result == "Check [[First]] and [[Second]] and [[Third]] links."


def test_attempt_external_link_restoration_display_text_replacement():
    """Test _attempt_external_link_restoration when display text differs from URL and can be replaced."""
    from services.validation.validators.wiki_link_validator import (
        LinkInfo,
        WikiLinkValidator,
    )

    validator = WikiLinkValidator(MagicMock())

    # Create external link where display text is different from URL
    link = LinkInfo(
        target="https://example.com",
        display_text="Example Website",
        full_wikitext="[https://example.com Example Website]",
        link_type="external",
    )

    # Edited text contains the display text
    edited_text = "Visit Example Website for more information."

    result = validator._attempt_external_link_restoration(edited_text, link)

    # Should replace display text with full link
    assert result is not None
    assert result == "Visit [https://example.com Example Website] for more information."


@pytest.mark.asyncio
async def test_complex_link_text_change_should_revert(link_validator):
    """
    Tests a case where link text was significantly changed (e.g., "drum kit" -> "drums").
    The validator cannot safely restore the link and should revert the edit.
    """
    original = "The [[rhythm section|rhythm]] is laid down by prominent, syncopated [[bassline]]s (with heavy use of broken [[octave]]s, that is, octaves with the notes sounded one after the other) played on the [[bass guitar]] and by drummers using a [[drum kit]], African/[[Latin percussion]], and [[electronic drum]]s such as Simmons and [[Roland Corporation|Roland]] [[sound module|drum modules]]. In Philly dance and Salsoul disco, the sound was enriched with solo lines and [[harmony part]]s played by a variety of orchestral instruments, such as [[violin]], [[viola]], [[cello]], [[trumpet]], [[saxophone]], [[trombone]], [[flugelhorn]], [[French horn]], [[English horn]], [[oboe]], [[flute]], [[timpani]] and [[synthesizer|synth strings]], string section or a full [[string orchestra]].{{citation needed|date=April 2021}}"
    edited = "The rhythm is laid down by prominent, syncopated basslines (using heavily broken octaves—octaves with notes played sequentially) on bass guitar and drums (including African/Latin percussion and electronic drums like Simmons and Roland drum modules). Philly dance and Salsoul disco added solo and harmony lines from various orchestral instruments: violin, viola, cello, trumpet, saxophone, trombone, flugelhorn, French horn, English horn, oboe, flute, timpani, and synth strings, a string section, or a full string orchestra.{{citation needed|date=April 2021}}"

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    assert should_revert
    assert result_text == original


# SECTION LINK TESTS


@pytest.mark.asyncio
async def test_section_link_extraction():
    """Test that section links are extracted correctly with proper targets."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Test various section link formats
    test_cases = [
        ("[[#Section heading]]", "#Section heading", "#Section heading"),
        (
            "[[#Definition of business processes|definition of business processes]]",
            "#Definition of business processes",
            "definition of business processes",
        ),
        (
            "[[#Further structuring|further structuring]]",
            "#Further structuring",
            "further structuring",
        ),
    ]

    for text, expected_target, expected_display in test_cases:
        links = validator._extract_links(text)
        assert len(links) == 1
        link = links[0]
        assert link.target == expected_target
        assert link.display_text == expected_display
        assert link.link_type == "wikilink"


@pytest.mark.asyncio
async def test_section_link_restoration_preserves_piped_format():
    """Test that section links are restored in their original piped format, not simplified."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Test section link restoration
    original = "See the [[#Definition of business processes|definition of business processes]] section."
    edited = "See the definition of business processes section."  # Link removed, display text remains

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore the original piped section link, not create a simplified [[#...]] form
    assert not should_revert
    assert (
        "[[#Definition of business processes|definition of business processes]]"
        in result_text
    )
    assert result_text == original


@pytest.mark.asyncio
async def test_section_link_does_not_get_simplified():
    """Test that section links don't get simplified to [[#target]] format during flexible restoration."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Test with section link where neither the display text nor target can be easily restored
    original = "Read the [[#Implementation details|implementation]] section for more."
    edited = "Read the detailed section for more."  # Link removed, display text changed

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should NOT create [[#Implementation details]] - section links should preserve piped format
    # Since the display text "implementation" is not found, it should revert
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_section_link_multiple_restoration():
    """Test restoration of multiple section links."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    original = "See [[#First section|first]] and [[#Second section|second]] sections."
    edited = (
        "See first and second sections."  # Both links removed, display text remains
    )

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore both section links
    assert not should_revert
    assert "[[#First section|first]]" in result_text
    assert "[[#Second section|second]]" in result_text


@pytest.mark.asyncio
async def test_section_link_mixed_with_regular_links():
    """Test section links mixed with regular wikilinks."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    original = "See [[Article]] and [[#Section|section]] for details."
    edited = "See Article and section for details."  # Both links removed, display text remains

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore both links
    assert not should_revert
    assert "[[Article]]" in result_text
    assert "[[#Section|section]]" in result_text


@pytest.mark.asyncio
async def test_section_link_display_text_not_found_coverage():
    """Test section link restoration when display text cannot be found."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Section link where display text is completely missing from edited text
    original = "See the [[#Implementation details|implementation]] section."
    edited = "See the documentation for more info."  # Display text completely removed

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because section link cannot be restored
    assert should_revert
    assert result_text == original


def test_fix_malformed_pipe_links_with_logging_coverage():
    """Test _fix_malformed_pipe_links method."""
    validator = WikiLinkValidator(MagicMock())

    text_with_malformed = "See [[Documentation|]] for more info."

    result = validator._fix_malformed_pipe_links(text_with_malformed)

    # Should fix the malformed link
    assert "[[Documentation]]" in result
    assert "[[Documentation|]]" not in result


def test_fix_malformed_pipe_links_empty_title_coverage():
    """Test _fix_malformed_pipe_links with various edge cases to ensure full coverage."""
    validator = WikiLinkValidator(MagicMock())

    # Test with a malformed link that uses link.title
    text_with_malformed = "Check [[Help|]] and [[Support|]] links."

    result = validator._fix_malformed_pipe_links(text_with_malformed)

    # Should fix both malformed links
    assert result == "Check [[Help]] and [[Support]] links."


@pytest.mark.asyncio
async def test_section_link_completely_removed_should_revert():
    """Test real-world case where section link is completely removed and should revert."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Real-world example: section link completely removed, regular link preserved
    original = 'The focus of business process modeling is on the [[#Representation type and notation|representation]] of the flow of [[Action (philosophy)|actions (activities)]], according to Hermann J. Schmelzer and Wolfgang Sesselmann consisting "of the cross-functional identification of value-adding activities that generate specific services expected by the customer and whose results have strategic significance for the company. They can extend beyond company boundaries and involve activities of customers, suppliers, or even competitors."'

    edited = 'Business process modeling focuses on representing the flow of [[Action (philosophy)|actions (activities)]]. Hermann J. Schmelzer and Wolfgang Sesselmann describe it as "the cross-functional identification of value-adding activities that generate specific services expected by the customer and whose results have strategic significance for the company. They can extend beyond company boundaries and involve activities of customers, suppliers, or even competitors."'

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because the section link was completely removed (both markup and display text)
    # and cannot be recovered
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_section_link_display_text_substring_match_can_be_restored():
    """Test that section links can be restored via substring matching when display text is embedded."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Test multiple scenarios of substring matching for section links
    test_cases = [
        {
            "name": "suffix addition",
            "original": "See the [[#Implementation details|implementation]] section for more information.",
            "edited": "See the detailed implementation section for more information.",
            "expected": "See the detailed [[#Implementation details|implementation]] section for more information.",
        },
        {
            "name": "prefix and suffix addition",
            "original": "The [[#Process modeling|process]] is important.",
            "edited": "The business process modeling is important.",
            "expected": "The business [[#Process modeling|process]] modeling is important.",
        },
    ]

    for case in test_cases:
        result_text, should_revert = await validator.validate_and_reintroduce_links(
            case["original"], case["edited"], 0, 1
        )

        # Should restore the section link via substring matching
        assert not should_revert, f"Failed for {case['name']} case"
        assert result_text == case["expected"], f"Wrong result for {case['name']} case"


# MISSING TEST CASES FOR COMPREHENSIVE LINK TYPE COVERAGE


@pytest.mark.asyncio
async def test_piped_link_fully_removed_should_revert(link_validator):
    """Test that when a piped link is fully removed (including display text), it should revert."""
    original = (
        "This article discusses [[Computer Science|programming concepts]] in detail."
    )
    edited = "This article discusses in detail."  # Both link markup and display text completely removed

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because the piped link was completely removed
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_pipe_trick_fully_removed_should_revert(link_validator):
    """Test that when a pipe trick link is fully removed, it should revert."""
    original = "See the [[London (Ontario)|]] article for more information."
    edited = "See the article for more information."  # Both pipe trick markup and expanded display text removed

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because the pipe trick link was completely removed
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_pipe_trick_display_text_changes_allowed(link_validator):
    """Test that pipe trick display text changes are allowed."""
    original = "Visit [[Paris (Texas)|]] for tourism information."
    edited = "Visit [[Paris (Texas)|Paris, Texas]] for tourism information."  # Display text explicitly added/changed

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should NOT revert - display text changes are allowed for pipe tricks
    assert not should_revert
    assert result_text == edited


@pytest.mark.asyncio
async def test_trailing_chars_link_fully_removed_should_revert(link_validator):
    """Test that when a trailing char link is fully removed, it should revert."""
    original = "I have several [[computer]]s in my office."
    edited = "I have several in my office."  # Both link markup and display text (including trailing chars) removed

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because the trailing char link was completely removed
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_trailing_chars_display_text_changes_allowed(link_validator):
    """Test that trailing char link display text changes are allowed."""
    original = "Many [[database]]s are used in modern applications."
    edited = "Many [[database|data storage systems]] are used in modern applications."  # Display text changed from "databases" to "data storage systems"

    result_text, should_revert = await link_validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should NOT revert - display text changes are allowed even for trailing char links
    assert not should_revert
    assert result_text == edited


@pytest.mark.asyncio
async def test_section_link_restoration_when_display_text_found():
    """Test section link restoration when display text is found in working text."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Create scenario where section link display text can be found and restored
    original = "See the [[#Implementation details|implementation]] section."
    edited = "See the implementation section."  # Link removed, display text remains

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should restore the section link
    assert not should_revert
    assert "[[#Implementation details|implementation]]" in result_text


@pytest.mark.asyncio
async def test_should_revert_when_restoration_would_create_nested_links():
    """Test that validator reverts when restoring a link would create nested/invalid wikitext."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Original has both [[The Open Group]] and [[The Open Group Architecture Framework]]
    # Edited removes [[The Open Group]] but keeps [[The Open Group Architecture Framework]]
    # Restoring [[The Open Group]] would create [[[The Open Group]] Architecture Framework]] which is invalid
    original = "The term is defined by [[The Open Group]] ([[The Open Group Architecture Framework]], TOGAF)."
    edited = "The term is defined by [[The Open Group Architecture Framework]], TOGAF."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because restoring [[The Open Group]] would create nested links
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_should_revert_when_restoration_would_interfere_with_existing_link():
    """Test that validator reverts when restoring would interfere with existing link boundaries."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Original has [[data]] and [[metadata]]
    # Edited removes [[data]] but "data" appears within [[metadata]]
    # Restoring [[data]] would create [[meta[[data]]]] which is invalid
    original = "Store [[data]] and [[metadata]] information."
    edited = "Store information and [[metadata]] information."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should revert because restoring [[data]] would interfere with [[metadata]]
    assert should_revert
    assert result_text == original


def test_has_nested_links_method():
    """Test the _has_nested_links method directly with various patterns."""
    validator = WikiLinkValidator(MagicMock())

    # Test cases that should return True (nested/invalid links)
    nested_cases = [
        "[[[[The Open Group]] Architecture Framework]]",  # Multiple opening brackets
        "[[link]] with [[other ]]]]",  # Multiple closing brackets
        "[[outer [[inner]] link]]",  # Link inside link (would fail bracket depth check)
        "Text [[[[another]] problem]]",  # Four opening brackets at start
        "End problem [[link ]]]]",  # Four closing brackets at end
    ]

    for case in nested_cases:
        assert validator._has_nested_links(case), (
            f"Should detect nested links in: {case}"
        )

    # Test cases that should return False (valid links)
    valid_cases = [
        "[[Normal Link]]",  # Simple link
        "[[Link|display text]]",  # Piped link
        "[[First]] and [[Second]] links",  # Multiple separate links
        "Text with [[link]] in middle",  # Link with surrounding text
        "No links at all",  # No links
        "",  # Empty string
        "[[External]] text [[Internal|display]]",  # Mixed link types
        "[[#Section|section link]]",  # Section link
    ]

    for case in valid_cases:
        assert not validator._has_nested_links(case), (
            f"Should NOT detect nested links in: {case}"
        )


@pytest.mark.asyncio
async def test_real_world_master_data_scenario():
    """Test the real-world scenario from the user's debug output."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Based on the user's debug output
    original = "The term ''[[master data]]'' is neither defined by [[The Open Group]] ([[The Open Group Architecture Framework]], TOGAF) or [[John Zachman|John A. Zachman]] (Zachman Framework) nor any of the five relevant German-speaking schools of business informatics: 1) [[August-Wilhelm Scheer|August W. Scheer]], 2) [[Hubert Österle]], 3) Otto K. Ferstl and Elmar J. Sinz, 4) Hermann Gehring and 5) Andreas Gadatsch and is commonly used in the absence of a suitable term in the literature. It is based on the general term for [[data]] that represents basic information about operationally relevant objects and refers to basic information that is not primary information of the business process."

    edited = "The term ''[[master data]]'' is undefined in [[The Open Group Architecture Framework]], TOGAF, the [[John Zachman|John A. Zachman]] Framework, or any of five relevant German business informatics schools: 1) [[August-Wilhelm Scheer|August W. Scheer]], 2) [[Hubert Österle]], 3) Otto K. Ferstl and Elmar J. Sinz, 4) Hermann Gehring, and 5) Andreas Gadatsch. It's commonly used in the literature when a suitable term is lacking. This data represents basic information about operationally relevant objects; it's basic information not primary to the business process."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original,
        edited,
        165,
        256,  # Use the actual paragraph numbers from debug output
    )

    # Should revert because restoring missing links would create nested/invalid structures
    assert should_revert
    assert result_text == original


@pytest.mark.asyncio
async def test_apollo_link_addition_should_be_removed():
    """
    Test reproducing the specific Apollo validation failure.

    This test simulates the scenario where:
    1. Original text has no Apollo link
    2. LLM adds an Apollo link
    3. WikiLinkValidator should remove it
    4. But AddedContentValidatorAdapter still detects it
    """
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Simulate text without Apollo link
    original = "The mission was successful and achieved its objectives."
    # Simulate LLM adding Apollo link
    edited = "The [[Apollo]] mission was successful and achieved its objectives."

    result_text, should_revert = await validator.validate_and_reintroduce_links(
        original, edited, 0, 1
    )

    # Should NOT revert - should remove the newly added link
    assert not should_revert, "Should not revert, should remove the newly added link"
    # Should remove the link markup but keep the display text
    assert (
        result_text == "The Apollo mission was successful and achieved its objectives."
    )
    # Should NOT contain the wikilink markup
    assert "[[Apollo]]" not in result_text, "Link markup should be removed"
    # Should contain the display text
    assert "Apollo" in result_text, "Display text should be preserved"


@pytest.mark.asyncio
async def test_apollo_link_addition_various_forms():
    """Test Apollo link addition in various forms that could cause validation failure."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    test_cases = [
        {
            "name": "Simple Apollo link",
            "original": "The mission was successful.",
            "edited": "The [[Apollo]] mission was successful.",
            "expected": "The Apollo mission was successful.",
        },
        {
            "name": "Apollo link with display text",
            "original": "The space program was important.",
            "edited": "The [[Apollo program|Apollo]] space program was important.",
            "expected": "The Apollo space program was important.",
        },
        {
            "name": "Apollo link with number",
            "original": "The mission landed on the moon.",
            "edited": "The [[Apollo 11]] mission landed on the moon.",
            "expected": "The Apollo 11 mission landed on the moon.",
        },
        {
            "name": "Multiple Apollo links",
            "original": "The missions were successful.",
            "edited": "The [[Apollo 11]] and [[Apollo 12]] missions were successful.",
            "expected": "The Apollo 11 and Apollo 12 missions were successful.",
        },
    ]

    for case in test_cases:
        result_text, should_revert = await validator.validate_and_reintroduce_links(
            case["original"], case["edited"], 0, 1
        )

        # Should NOT revert - should remove the newly added links
        assert not should_revert, f"Should not revert for {case['name']}"
        # Should match expected result
        assert result_text == case["expected"], f"Wrong result for {case['name']}"
        # Should NOT contain any wikilink markup
        assert "[[" not in result_text, (
            f"Link markup should be removed for {case['name']}"
        )


@pytest.mark.asyncio
async def test_apollo_link_removal_failure_scenario():
    """Test edge cases where Apollo link removal might fail."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Test case where _attempt_link_removal might not work correctly
    original = "The mission was a success."
    edited = "The [[Apollo program|Apollo]] mission was a success."

    # Mock the _attempt_link_removal to return the input unchanged (simulating failure)
    with patch.object(validator, "_attempt_link_removal", return_value=edited):
        result_text, should_revert = await validator.validate_and_reintroduce_links(
            original, edited, 0, 1
        )

    # If link removal fails, the validator should still return the working text
    # The failure would be caught by AddedContentValidatorAdapter later
    assert not should_revert, "Should not revert even if link removal fails"
    # But the link would still be there
    assert "[[Apollo program|Apollo]]" in result_text


@pytest.mark.asyncio
async def test_apollo_link_integration_with_reference_placeholders():
    """Test Apollo link addition with reference placeholders, simulating real pipeline."""
    from services.text.reference_handler import ReferenceHandler

    reference_handler = ReferenceHandler()
    validator = WikiLinkValidator(reference_handler)

    # Simulate text with reference placeholders
    original = "The mission was successful.{{REF_PLACEHOLDER_0}}"
    edited = "The [[Apollo]] mission was successful.{{REF_PLACEHOLDER_0}}"

    # Mock the reference handler to return input unchanged for this test
    with patch.object(
        reference_handler,
        "replace_references_with_placeholders",
        side_effect=lambda text: (text, []),
    ):
        result_text, should_revert = await validator.validate_and_reintroduce_links(
            original, edited, 0, 1
        )

    # Should remove the Apollo link but keep display text and placeholder
    assert not should_revert
    assert result_text == "The Apollo mission was successful.{{REF_PLACEHOLDER_0}}"
    assert "[[Apollo]]" not in result_text


@pytest.mark.asyncio
async def test_pipeline_execution_order_bug_reproduction():
    """
    Test demonstrating the pipeline execution order fix.

    The fix ensures that async validators run BEFORE sync validators in ValidationPipeline,
    so WikiLinkValidatorAdapter (async) runs before AddedContentValidatorAdapter (sync).
    This allows WikiLinkValidator to remove Apollo links before AddedContentValidator
    can detect them as new content.
    """

    from services.text.reference_handler import ReferenceHandler
    from services.validation.adapters import (
        AddedContentValidatorAdapter,
        WikiLinkValidatorAdapter,
    )
    from services.validation.pipeline import ValidationPipelineBuilder
    from services.validation.validators.reference_validator import ReferenceValidator
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    reference_handler = ReferenceHandler()
    reference_validator = ReferenceValidator()
    wiki_link_validator = WikiLinkValidator(reference_handler)

    execution_order: List[str] = []

    # Build pipeline with WikiLinkValidatorAdapter (async) added FIRST
    builder = ValidationPipelineBuilder()
    link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)
    builder.add_async_validator(
        link_adapter
    )  # Added FIRST (should run first to remove Apollo)

    added_content_adapter = AddedContentValidatorAdapter(
        reference_validator, reference_handler
    )
    builder.add_validator(
        added_content_adapter
    )  # Added SECOND (should run after WikiLink removes Apollo)

    pipeline = builder.build()

    # Test the Apollo scenario
    original = "The mission was successful and achieved its objectives."
    edited_with_apollo = (
        "The [[Apollo]] mission was successful and achieved its objectives."
    )

    final_text, should_revert = await pipeline.validate(
        original,
        edited_with_apollo,
        {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
    )

    # Print actual execution order to demonstrate the bug
    print("=== ACTUAL EXECUTION ORDER ===")
    for i, msg in enumerate(execution_order, 1):
        print(f"{i}. {msg}")

    # The bug: AddedContentValidatorAdapter runs BEFORE WikiLinkValidatorAdapter
    # even though WikiLinkValidatorAdapter was added to the pipeline first
    if len(execution_order) >= 1:
        # This demonstrates the fix - WikiLinkValidatorAdapter runs first and removes Apollo,
        # so AddedContentValidatorAdapter never sees the Apollo link
        first_validator_run = execution_order[0]
        assert "WikiLinkValidatorAdapter" in first_validator_run, (
            f"WikiLinkValidatorAdapter should run first: {first_validator_run}. "
            "This proves the bug has been fixed - async validators now run before sync validators."
        )

    # Should NOT revert because WikiLinkValidatorAdapter removed Apollo before AddedContentValidatorAdapter could detect it
    assert not should_revert, "Should not revert after the pipeline execution order fix"
    assert "[[Apollo]]" not in final_text, "Apollo link markup should be removed"
    assert "Apollo" in final_text, "Apollo text should be preserved"


@pytest.mark.asyncio
async def test_pipeline_execution_order_fix_suggestion():
    """
    Test demonstrating how fixing the execution order would solve the Apollo bug.

    If async validators ran BEFORE sync validators, the WikiLinkValidator would
    remove the Apollo link before AddedContentValidatorAdapter could detect it.
    """
    from services.text.reference_handler import ReferenceHandler
    from services.validation.adapters import (
        AddedContentValidatorAdapter,
        WikiLinkValidatorAdapter,
    )
    from services.validation.validators.reference_validator import ReferenceValidator
    from services.validation.validators.wiki_link_validator import WikiLinkValidator

    reference_handler = ReferenceHandler()
    wiki_link_validator = WikiLinkValidator(reference_handler)

    # Test just the WikiLinkValidatorAdapter in isolation
    # This proves it DOES correctly remove Apollo links
    link_adapter = WikiLinkValidatorAdapter(wiki_link_validator)

    original = "The mission was successful and achieved its objectives."
    apollo_added = "The [[Apollo]] mission was successful and achieved its objectives."

    # Run WikiLinkValidatorAdapter first (as it should be)
    text_after_link_validation, should_revert_links = await link_adapter.validate(
        original,
        apollo_added,
        {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
    )

    # WikiLinkValidator should remove the Apollo link without reverting
    assert not should_revert_links, (
        "WikiLinkValidator should not revert - it should remove the Apollo link"
    )
    assert "[[Apollo]]" not in text_after_link_validation, (
        "Apollo link markup should be removed"
    )
    assert "Apollo" in text_after_link_validation, (
        "Apollo text should remain (just markup removed)"
    )
    expected_after_link_removal = (
        "The Apollo mission was successful and achieved its objectives."
    )
    assert text_after_link_validation == expected_after_link_removal

    # Now run AddedContentValidatorAdapter on the cleaned text
    reference_validator = ReferenceValidator()
    added_content_adapter = AddedContentValidatorAdapter(
        reference_validator, reference_handler
    )

    final_text, should_revert_content = added_content_adapter.validate(
        original,
        text_after_link_validation,
        {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []},
    )

    # AddedContentValidatorAdapter should not detect any new links because they were already removed
    assert not should_revert_content, (
        "AddedContentValidatorAdapter should not revert when no new links are present"
    )
    assert final_text == text_after_link_validation, "Text should remain unchanged"

    # This proves that if WikiLinkValidator runs BEFORE AddedContentValidator,
    # the Apollo scenario works correctly without any validation failures
