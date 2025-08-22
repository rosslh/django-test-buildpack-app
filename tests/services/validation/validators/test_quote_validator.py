import pytest

from services.validation.validators.quote_validator import QuoteValidator


@pytest.fixture
def quote_validator():
    """Fixture for QuoteValidator."""

    validator = QuoteValidator()
    return validator


def test_validate_no_change(quote_validator):
    """Test that no revert is needed when quotes are unchanged."""
    validator = quote_validator
    original = 'This is a "quote".'
    edited = 'This is a "quote".'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_validate_quote_removed(quote_validator):
    """Test that a revert is triggered when a quote is removed."""
    validator = quote_validator
    original = 'This is a "quote".'
    edited = "This is a ."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert revert
    assert corrected == original


def test_validate_quote_added(quote_validator):
    """Test that a revert is triggered when a quote is added."""
    validator = quote_validator
    original = "This is a test."
    edited = 'This is a "quote" test.'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == "This is a quote test."


def test_validate_quote_modified(quote_validator):
    """Test that a revert is triggered when a quote is modified."""
    validator = quote_validator
    original = 'This is a "quote1".'
    edited = 'This is a "quote2".'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert revert
    assert corrected == original


def test_validate_multiple_quotes_reordered(quote_validator):
    """Test that reordering quotes does not trigger a revert."""
    validator = quote_validator
    original = '"quote1" "quote2"'
    edited = '"quote2" "quote1"'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_validate_with_no_quotes(quote_validator):
    """Test with text that contains no quotes."""
    validator = quote_validator
    original = "Text with no quotes."
    edited = "Edited text with no quotes."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_validate_italics_changed_to_quotes_is_corrected(quote_validator):
    """Test that changing wikitext italics to quotes is corrected."""
    validator = quote_validator
    original = "This is ''italic'' text."
    edited = 'This is "italic" text.'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_validate_bold_changed_to_quotes_is_corrected(quote_validator):
    """Test that changing wikitext bold to quotes is corrected."""
    validator = quote_validator
    original = "This is '''bold''' text."
    edited = 'This is "bold" text.'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # The quote is converted back to bold formatting, maintaining the original
    assert corrected == original


def test_validate_removed_quotes_are_readded(quote_validator):
    """Test that removed quotes are re-added if the text is present."""
    validator = quote_validator
    original = 'This is "a quote" from a book.'
    edited = "This is a quote from a book."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_restore_italic_formatting(quote_validator):
    """Test that italic formatting is restored when display text is present."""
    validator = quote_validator
    original = "This is ''italic'' text."
    edited = "This is italic text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_restore_bold_formatting(quote_validator):
    """Test that bold formatting is restored when display text is present."""
    validator = quote_validator
    original = "This is '''bold''' text."
    edited = "This is bold text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_restore_multiple_italic_bold_formatting(quote_validator):
    """Test that multiple italic and bold formatting is restored."""
    validator = quote_validator
    original = "This is ''italic'' and '''bold''' text."
    edited = "This is italic and bold text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original
    # Bold is processed first, then italic


def test_no_restore_when_formatting_intact(quote_validator):
    """Test that no restoration occurs when formatting is already intact."""
    validator = quote_validator
    original = "This is ''italic'' text."
    edited = "This is ''italic'' text with more words."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_no_restore_when_text_not_present(quote_validator):
    """Test that no restoration occurs when the display text is not present."""
    validator = quote_validator
    original = "This is ''italic'' text."
    edited = "This is different text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_restore_partial_text_match(quote_validator):
    """Test that restoration only happens for exact text matches."""
    validator = quote_validator
    original = "This is ''important'' text."
    edited = "This is important and vital text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == "This is ''important'' and vital text."


def test_validate_removed_quotes_text_missing_triggers_revert(quote_validator):
    """Test that a revert is triggered when quote text is completely missing."""
    validator = quote_validator
    original = 'This is "a missing quote" from text.'
    edited = "This is from text."  # Quote text completely removed
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert revert
    assert corrected == original


def test_restore_italic_formatting_with_non_ascii(quote_validator):
    """Test that italic formatting is restored with non-ASCII characters."""
    validator = quote_validator
    original = "This is ''Timo Füermann'' text."
    edited = "This is Timo Füermann text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_no_double_wrap_italic_with_trailing_punctuation(quote_validator):
    """Test that italics with trailing punctuation are not double-wrapped."""
    validator = quote_validator
    original = "processes in the ''control view'' and vice versa"
    edited = (
        "processes in the ''control view,'' and vice versa"  # Added comma after italics
    )
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited  # Should not change


def test_no_double_wrap_bold_with_trailing_punctuation(quote_validator):
    """Test that bold with trailing punctuation is not double-wrapped."""
    validator = quote_validator
    original = "processes in the '''control view''' and vice versa"
    edited = (
        "processes in the '''control view,''' and vice versa"  # Added comma after bold
    )
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited  # Should not change


def test_no_introduce_formatting_around_existing_quotes(quote_validator):
    """Test that formatting is not introduced around existing quotes."""
    validator = quote_validator
    original = 'This is a "control view" example.'
    edited = 'This is a "control view," example.'  # Added comma after quotes
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited  # Should not change


def test_no_introduce_quotes_around_existing_italics(quote_validator):
    """Test that quotes are not introduced around existing italics."""
    validator = quote_validator
    original = "This is ''italic'' text."
    edited = "This is ''italic,'' text."  # Added comma after italics
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited  # Should not change


def test_complex_control_view_bug_reproduction(quote_validator):
    """Test that reproduces the specific control view bug."""
    validator = quote_validator
    original = "as processes in the ''control view'' and vice versa"
    edited = "as processes in the ''control view,'' and vice versa"  # LLM added comma
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited  # Should not double-wrap


def test_quotes_equivalent_with_different_lengths(quote_validator):
    """Test that quotes with different lengths are not considered equivalent."""
    validator = quote_validator
    # This should trigger the length check in _are_quotes_equivalent_with_punctuation
    original = 'This has "one quote".'
    edited = 'This has "one quote" and "another quote".'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == 'This has "one quote" and another quote.'


def test_removed_quotes_cannot_be_readded(quote_validator):
    """Test that a revert is triggered when removed quote text is completely missing."""
    validator = quote_validator
    original = 'This is "a quote" and "another quote" text.'
    edited = "This is different text."  # Both quotes completely removed
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert revert
    assert corrected == original


def test_text_within_quotes_with_punctuation_detection(quote_validator):
    """Test that text within quotes with punctuation is properly detected."""
    validator = quote_validator
    # This should trigger the quote removal logic for newly added quotes
    original = "This is ''important'' text."
    edited = 'This is "important," text.'  # important is within quotes with comma
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # The quote should be removed as a newly added quote since it doesn't match the italic
    assert corrected == "This is important, text."


def test_restore_partial_italic_formatting_loss(quote_validator):
    """Test that italic formatting is restored when removed from some but not all words."""
    validator = quote_validator
    original = "In practice, combinations of ''informal'', ''semiformal'' and ''formal'' models are common"
    edited = "In practice, combinations of ''informal'', ''semiformal'' and formal models are common"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_restore_partial_bold_formatting_loss(quote_validator):
    """Test that bold formatting is restored when removed from some but not all words."""
    validator = quote_validator
    original = "Important concepts include '''security''', '''privacy''' and '''reliability''' measures"
    edited = "Important concepts include '''security''', '''privacy''' and reliability measures"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


def test_restore_partial_single_quote_loss(quote_validator):
    """Test that single quotes are no longer validated (removed functionality)."""
    validator = quote_validator
    original = "The terms 'first option', 'second option' and 'third option' are used"
    edited = "The terms 'first option', 'second option' and third option are used"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert (
        corrected == edited
    )  # No longer corrected since single quotes are not validated


def test_restore_partial_double_quote_loss(quote_validator):
    """Test that double quotes are restored when removed from some but not all phrases."""
    validator = quote_validator
    original = 'The phrases "hello world", "goodbye world" and "nice world" are common'
    edited = 'The phrases "hello world", "goodbye world" and nice world are common'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == original


# New tests to cover missing lines for 99% coverage:


def test_single_quote_modification_no_longer_validated(quote_validator):
    """Test that single quote modification no longer triggers revert (removed functionality)."""
    validator = quote_validator
    original = "He said 'hello world' to me."
    edited = "He said 'goodbye world' to me."  # Single quote content changed
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert  # No longer reverted since single quotes are not validated
    assert corrected == edited  # No correction needed


def test_bold_changed_to_single_quotes_no_longer_corrected(quote_validator):
    """Test that changing wikitext bold to single quotes is no longer corrected (removed functionality)."""
    validator = quote_validator
    original = "This is '''important''' text."
    edited = "This is 'important' text."  # Bold changed to single quotes
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert (
        corrected == edited
    )  # No longer corrected since single quotes are not validated


def test_italic_changed_to_single_quotes_no_longer_corrected(quote_validator):
    """Test that changing wikitext italic to single quotes is no longer corrected (removed functionality)."""
    validator = quote_validator
    original = "This is ''important'' text."
    edited = "This is 'important' text."  # Italic changed to single quotes
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert (
        corrected == edited
    )  # No longer corrected since single quotes are not validated


def test_is_within_quotes_regex_match_coverage(quote_validator):
    """Test to ensure we cover the regex match in _is_within_quotes."""
    validator = quote_validator

    # Test to ensure we hit the regex match check in _is_within_quotes
    text = '"text123"'  # Word characters after the target
    pos = 1  # Position of 't' in 'text'
    target = "text"  # Target that doesn't contain all the word chars after

    # This should hit the regex match check and return False due to word chars between text and quote
    result = validator._is_within_quotes(text, pos, target, '"')
    # The regex should NOT match (return None) because there are word chars between target and closing quote
    assert not result


def test_is_within_quotes_no_closing_quote(quote_validator):
    """Test _is_within_quotes when there's no closing quote."""
    validator = quote_validator

    # Test case where there's no closing quote character
    text = '"incomplete quote text'
    pos = 1  # Position of 'i' in 'incomplete'
    target = "incomplete"

    # Should return False because there's no closing quote
    assert not validator._is_within_quotes(text, pos, target, '"')

    # Test with single quote too (though single quotes are no longer validated)
    text = "'incomplete quote text"
    assert not validator._is_within_quotes(text, pos, target, "'")


def test_is_within_quotes_with_non_word_between(quote_validator):
    """Test _is_within_quotes with non-word characters between text and closing quote."""
    validator = quote_validator

    # Test case where there are only punctuation marks between text and closing quote
    text = '"text!"'
    pos = 1  # Position of 't' in 'text'
    target = "text"

    # Should return True because only punctuation is allowed between text and closing quote
    assert validator._is_within_quotes(text, pos, target, '"')


def test_is_within_quotes_edge_cases(quote_validator):
    """Test _is_within_quotes edge cases to cover remaining branches."""
    validator = quote_validator

    # Test case where quote char is found but between_text has word characters
    text = '"text more words"'
    pos = 1  # Position of 't' in 'text'
    target = "text"

    # Should return False because there are word characters between text and closing quote
    assert not validator._is_within_quotes(text, pos, target, '"')

    # Test case where target is not immediately after quote char
    text = "hello text"  # No quotes at all
    pos = 6  # Position of 't' in 'text'
    target = "text"

    # Should return False because there's no quote before the target
    assert not validator._is_within_quotes(text, pos, target, '"')


# New test to cover remaining uncovered lines:
def test_is_within_quotes_return_false_branch(quote_validator):
    """Test _is_within_quotes to ensure we hit the final return False."""
    validator = quote_validator

    # Case where pos <= 0 to hit the final return False
    text = 'text "quoted"'
    pos = 0  # Position 0, so pos > 0 is False
    target = "text"

    # Should return False because pos is 0, not > 0
    assert not validator._is_within_quotes(text, pos, target, '"')


def test_restore_nested_italics_bug(quote_validator):
    """Test to reproduce the bug where italics are restored inside other italics."""
    validator = quote_validator
    original = "This is ''corporate function'' and another ''function''."
    edited = "This is ''corporate'' function and another function."  # LLM split and de-italicized 'function'
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # It should re-italicize the standalone 'function' but not the one that was part of another italic block.
    assert corrected == "This is ''corporate'' function and another ''function''."


def test_no_restore_quotes_inside_bold(quote_validator):
    """Test that quotes are not restored inside bold formatting."""
    validator = quote_validator
    original = "This is '''bold \"quote\" text''' and a \"quote\"."
    edited = "This is '''bold quote text''' and a quote."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == "This is '''bold quote text''' and a \"quote\"."


def test_no_restore_bold_inside_italics(quote_validator):
    """Test that bold formatting is not restored inside italic formatting."""
    validator = quote_validator
    original = "This is ''italic '''bold''' text'' and '''bold'''."
    edited = "This is ''italic bold text'' and bold."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == "This is ''italic bold text'' and '''bold'''."


def test_bold_italic_combination_unchanged(quote_validator):
    """Test that existing text with both bold and italic formatting remains unchanged."""
    validator = quote_validator
    original = "This is '''''bold and italic''''' text."
    edited = "This is '''''bold and italic''''' text with more content."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_single_apostrophes_unchanged(quote_validator):
    """Test that single apostrophes in contractions remain unchanged."""
    validator = quote_validator
    original = "I don't think we can't solve this problem, it's too hard."
    edited = "I don't think we can't solve this problem easily, it's too hard."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_added_single_apostrophes_unchanged(quote_validator):
    """Test that added single apostrophes in contractions remain unchanged."""
    validator = quote_validator
    original = "I do not think we cannot solve this problem."
    edited = "I don't think we can't solve this problem."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    assert corrected == edited


def test_is_within_formatting_block_return_false(quote_validator):
    """Test that _is_within_formatting_block returns False when target is not within any blocks."""
    validator = quote_validator

    # Test case where target is not within any formatting blocks (covers return False line)
    text = "normal target text"
    pos = 7  # Position of 'target'
    target = "target"
    assert not validator._is_within_formatting_block(text, pos, target)


def test_handle_quote_changes_return_none(quote_validator):
    """Test that _handle_quote_changes returns None for certain cases."""
    validator = quote_validator

    # Test case where both quotes are added and removed (covers final return None)
    original_quotes = ["original"]
    edited_quotes = ["new"]
    result = validator._handle_quote_changes(
        "text", original_quotes, edited_quotes, '"'
    )
    assert result is None


def test_would_create_invalid_syntax_all_cases(quote_validator):
    """Test _would_create_invalid_syntax for all reachable conditions."""
    validator = quote_validator

    # Test return True after before_text.endswith("''")
    text = "text''  word"  # '' followed by whitespace then word
    pos = 8  # Position of 'word' after '' with whitespace
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result

    # Test return True after before_text.endswith("'''")
    text = "text'''  word"  # ''' followed by whitespace then word
    pos = 9  # Position of 'word' after ''' with whitespace
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result

    # Test return True after before_text.endswith('"')
    text = 'text"  word'  # " followed by whitespace then word
    pos = 7  # Position of 'word' after " with whitespace
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result

    # Test return True after after_text.startswith("''")
    text = "word  ''text"  # word followed by whitespace then ''
    pos = 0  # Position of 'word' before '' with whitespace
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result

    # Test return True after after_text.startswith("'''")
    text = "word  '''text"  # word followed by whitespace then '''
    pos = 0  # Position of 'word' before ''' with whitespace
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result

    # Test return True after after_text.startswith('"')
    text = 'word  "text'  # word followed by whitespace then "
    pos = 0  # Position of 'word' before " with whitespace
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result


def test_would_create_invalid_syntax_italic_endswith_specific(quote_validator):
    """Test to specifically hit before_text.endswith('')"""
    validator = quote_validator

    # Create a case where only the italic endswith condition is met, not bold or quote
    text = "some''   target"  # Double quotes at end, with spaces before target
    pos = 9  # Position of 'target'
    target = "target"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result


def test_would_create_invalid_syntax_italic_startswith_specific(quote_validator):
    """Test to specifically hit after_text.startswith('')"""
    validator = quote_validator

    # Create a case where only the italic startswith condition is met
    text = "target   ''after"  # Italic quotes after target with spaces
    pos = 0  # Position of 'target'
    target = "target"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result


def test_would_create_invalid_syntax_negative_cases(quote_validator):
    """Test cases where _would_create_invalid_syntax should return False."""
    validator = quote_validator

    # Test cases that should return False (don't create invalid syntax)
    text = "normal word text"
    pos = 7  # Position of 'word'
    target = "word"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert not result

    # Another case that should be safe
    text = "some text here"
    pos = 5  # Position of 'text'
    target = "text"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert not result


def test_no_restore_quotes_within_square_brackets(quote_validator):
    """Test that quotes are not restored within square brackets (wikilinks)."""
    validator = quote_validator
    original = 'This is a "quote" and [[link "with quote" inside]].'
    edited = "This is a quote and [[link with quote inside]]."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside square brackets
    assert corrected == 'This is a "quote" and [[link with quote inside]].'


def test_no_restore_bold_within_square_brackets(quote_validator):
    """Test that bold formatting is not restored within square brackets."""
    validator = quote_validator
    original = "This is '''bold''' and [[link '''with bold''' inside]]."
    edited = "This is bold and [[link with bold inside]]."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone bold but not the one inside square brackets
    assert corrected == "This is '''bold''' and [[link with bold inside]]."


def test_no_restore_italic_within_square_brackets(quote_validator):
    """Test that italic formatting is not restored within square brackets."""
    validator = quote_validator
    original = "This is ''italic'' and [[link ''with italic'' inside]]."
    edited = "This is italic and [[link with italic inside]]."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone italic but not the one inside square brackets
    assert corrected == "This is ''italic'' and [[link with italic inside]]."


def test_no_restore_within_nested_square_brackets(quote_validator):
    """Test that formatting is not restored within nested square brackets."""
    validator = quote_validator
    original = "Text ''italic'' and [[File:image.jpg|thumb|''italic caption'']]."
    edited = "Text italic and [[File:image.jpg|thumb|italic caption]]."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone italic but not the one inside square brackets
    assert corrected == "Text ''italic'' and [[File:image.jpg|thumb|italic caption]]."


def test_no_restore_within_complex_wikilink(quote_validator):
    """Test that formatting is not restored within complex wikilinks with multiple parts."""
    validator = quote_validator
    original = 'A "quote" and [[Category:Test|"quoted category"]] link.'
    edited = "A quote and [[Category:Test|quoted category]] link."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside the category link
    assert corrected == 'A "quote" and [[Category:Test|quoted category]] link.'


def test_restore_multiple_formatting_outside_brackets_only(quote_validator):
    """Test that multiple formatting types are restored outside but not inside brackets."""
    validator = quote_validator
    original = """Text "quote", ''italic'', '''bold''' and [[link "quote" ''italic'' '''bold''']]."""
    edited = "Text quote, italic, bold and [[link quote italic bold]]."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore all formatting outside brackets but none inside
    expected = (
        """Text "quote", ''italic'', '''bold''' and [[link quote italic bold]]."""
    )
    assert corrected == expected


def test_square_brackets_at_text_boundaries(quote_validator):
    """Test that square brackets at the beginning or end of text are handled correctly."""
    validator = quote_validator
    original = '[[File:test.jpg|"caption"]] and "quote" text.'
    edited = "[[File:test.jpg|caption]] and quote text."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one in the file caption
    assert corrected == '[[File:test.jpg|caption]] and "quote" text.'


def test_malformed_square_brackets_ignored(quote_validator):
    """Test that malformed square brackets don't interfere with restoration."""
    validator = quote_validator
    original = 'Text "quote" and [incomplete bracket with "quote".'
    edited = "Text quote and [incomplete bracket with quote."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore both quotes since the brackets are malformed (not a complete pair)
    assert corrected == 'Text "quote" and [incomplete bracket with "quote".'


def test_empty_square_brackets(quote_validator):
    """Test that empty square brackets don't interfere with restoration."""
    validator = quote_validator
    original = 'Text "quote" and [] empty brackets.'
    edited = "Text quote and [] empty brackets."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the quote since empty brackets don't contain the quote
    assert corrected == 'Text "quote" and [] empty brackets.'


def test_adjacent_square_brackets(quote_validator):
    """Test handling of adjacent square brackets."""
    validator = quote_validator
    original = 'Text [[link1 "quote1"]][[link2 "quote2"]] and "quote3".'
    edited = "Text [[link1 quote1]][[link2 quote2]] and quote3."
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore only the standalone quote
    assert corrected == 'Text [[link1 quote1]][[link2 quote2]] and "quote3".'


def test_no_restore_within_templates(quote_validator):
    """Test that formatting is not restored within template blocks."""
    validator = quote_validator
    original = 'Text "quote" and {{template|"param with quote"}}'
    edited = "Text quote and {{template|param with quote}}"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside template
    assert corrected == 'Text "quote" and {{template|param with quote}}'


def test_no_restore_within_references(quote_validator):
    """Test that formatting is not restored within reference blocks."""
    validator = quote_validator
    original = 'Text "quote" and <ref>"Reference with quote"</ref>'
    edited = "Text quote and <ref>Reference with quote</ref>"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside reference
    assert corrected == 'Text "quote" and <ref>Reference with quote</ref>'


def test_no_restore_within_nowiki(quote_validator):
    """Test that formatting is not restored within nowiki blocks."""
    validator = quote_validator
    original = 'Text "quote" and <nowiki>"Nowiki with quote"</nowiki>'
    edited = "Text quote and <nowiki>Nowiki with quote</nowiki>"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside nowiki
    assert corrected == 'Text "quote" and <nowiki>Nowiki with quote</nowiki>'


def test_no_restore_within_code_tags(quote_validator):
    """Test that formatting is not restored within code tags."""
    validator = quote_validator
    original = 'Text "quote" and <code>"Code with quote"</code>'
    edited = "Text quote and <code>Code with quote</code>"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside code
    assert corrected == 'Text "quote" and <code>Code with quote</code>'


def test_no_restore_within_pre_tags(quote_validator):
    """Test that formatting is not restored within pre tags."""
    validator = quote_validator
    original = 'Text "quote" and <pre>"Pre with quote"</pre>'
    edited = "Text quote and <pre>Pre with quote</pre>"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside pre
    assert corrected == 'Text "quote" and <pre>Pre with quote</pre>'


def test_no_restore_within_math_tags(quote_validator):
    """Test that formatting is not restored within math tags."""
    validator = quote_validator
    original = 'Text "quote" and <math>"Math with quote"</math>'
    edited = "Text quote and <math>Math with quote</math>"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside math
    assert corrected == 'Text "quote" and <math>Math with quote</math>'


def test_no_restore_within_syntaxhighlight_tags(quote_validator):
    """Test that formatting is not restored within syntaxhighlight tags."""
    validator = quote_validator
    original = 'Text "quote" and <syntaxhighlight>"Code with quote"</syntaxhighlight>'
    edited = "Text quote and <syntaxhighlight>Code with quote</syntaxhighlight>"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside syntaxhighlight
    assert (
        corrected
        == 'Text "quote" and <syntaxhighlight>Code with quote</syntaxhighlight>'
    )


def test_no_restore_within_comments(quote_validator):
    """Test that formatting is not restored within comment blocks."""
    validator = quote_validator
    original = 'Text "quote" and <!-- "Comment with quote" -->'
    edited = "Text quote and <!-- Comment with quote -->"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside comment
    assert corrected == 'Text "quote" and <!-- Comment with quote -->'


def test_no_restore_within_external_links(quote_validator):
    """Test that formatting is not restored within external link blocks."""
    validator = quote_validator
    original = 'Text "quote" and [http://example.com "Link with quote"]'
    edited = "Text quote and [http://example.com Link with quote]"
    corrected, revert = validator.validate_and_correct(original, edited, 0, 1)
    assert not revert
    # Should restore the standalone quote but not the one inside external link
    assert corrected == 'Text "quote" and [http://example.com Link with quote]'


def test_format_revert_message(quote_validator):
    """Test the _format_revert_message method to reach missing coverage."""
    validator = quote_validator

    # Test with both added and removed items
    message = validator._format_revert_message(["added1", "added2"], ["removed1"])
    expected = "WARNING: Quotes were modified. Removed: ['removed1'] Added: ['added1', 'added2']. Reverting."
    assert message == expected

    # Test with only removed items
    message = validator._format_revert_message([], ["removed1", "removed2"])
    expected = (
        "WARNING: Quotes were modified. Removed: ['removed1', 'removed2']. Reverting."
    )
    assert message == expected

    # Test with only added items
    message = validator._format_revert_message(["added1"], [])
    expected = "WARNING: Quotes were modified. Added: ['added1']. Reverting."
    assert message == expected

    # Test with no items (edge case)
    message = validator._format_revert_message([], [])
    expected = "WARNING: Quotes were modified.. Reverting."
    assert message == expected


def test_would_create_invalid_syntax_bold_markup(quote_validator):
    """Test that bold markup (''') is properly detected as invalid syntax."""
    validator = quote_validator

    # Test bold markup before target (should be caught by '' check since ''' ends with '')
    text = "text'''target"  # Triple quote immediately before target (no whitespace)
    pos = 7  # Position of 'target' right after '''
    target = "target"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result

    # Test bold markup after target (should be caught by '' check since ''' starts with '')
    text = "target'''after"  # Triple quote immediately after target (no whitespace)
    pos = 0  # Position of 'target' right before '''
    target = "target"
    result = validator._would_create_invalid_syntax(text, pos, target)
    assert result
