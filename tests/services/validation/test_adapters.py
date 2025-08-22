"""Tests for validator adapter classes."""

import unittest
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from services.core.interfaces import IReferenceHandler
from services.text.reference_handler import ReferenceHandler
from services.tracking.reversion_tracker import ReversionType
from services.validation import (
    ListMarkerValidator,
    ReferenceValidator,
    SpellingValidator,
    WikiLinkValidator,
)
from services.validation.adapters import (
    AddedContentValidatorAdapter,
    CompositeReferenceValidatorAdapter,
    ListMarkerValidatorAdapter,
    MetaCommentaryValidatorAdapter,
    QuoteValidatorAdapter,
    ReferenceContentValidatorAdapter,
    ReferenceValidatorAdapter,
    SpellingValidatorAdapter,
    TemplateValidatorAdapter,
    WikiLinkValidatorAdapter,
)
from services.validation.validators.quote_validator import QuoteValidator
from services.validation.validators.template_validator import TemplateValidator


@pytest.fixture
def mock_reference_handler():
    """Fixture for a mock ReferenceHandler instance."""
    handler = Mock(spec=ReferenceHandler)
    handler.replace_references_with_placeholders.side_effect = lambda text: (text, [])
    handler.restore_references.side_effect = lambda text, refs: text
    return handler


class TestWikiLinkValidatorAdapter:
    """Test WikiLinkValidatorAdapter class."""

    @pytest.mark.asyncio
    async def test_validate_calls_wrapped_validator(self):
        """Test that validate calls the wrapped validator correctly."""
        # Arrange
        mock_validator = Mock(spec=WikiLinkValidator)
        mock_validator.validate_and_reintroduce_links = AsyncMock(
            return_value=("edited text", False)
        )
        adapter = WikiLinkValidatorAdapter(mock_validator)

        original = "original text [[link]]"
        edited = "edited text [[link]]"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = await adapter.validate(original, edited, context)

        # Assert
        assert result_text == "edited text"
        assert should_revert is False
        mock_validator.validate_and_reintroduce_links.assert_called_once_with(
            original_paragraph_content=original,
            edited_text_with_placeholders=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    @pytest.mark.asyncio
    async def test_validate_with_reversion(self):
        """Test validate when wrapped validator indicates reversion."""
        # Arrange
        mock_validator = Mock(spec=WikiLinkValidator)
        mock_validator.validate_and_reintroduce_links = AsyncMock(
            return_value=("original text", True)
        )
        adapter = WikiLinkValidatorAdapter(mock_validator)

        original = "original text [[link]]"
        edited = "edited text"
        context = {"paragraph_index": 2, "total_paragraphs": 5}

        # Act
        result_text, should_revert = await adapter.validate(original, edited, context)

        # Assert
        assert result_text == "original text"
        assert should_revert is True

    def test_get_last_failure_reason_none(self):
        mock_validator = Mock(spec=WikiLinkValidator)
        adapter = WikiLinkValidatorAdapter(mock_validator)
        assert adapter.get_last_failure_reason() is None

    @pytest.mark.asyncio
    async def test_validate_with_text_modification_not_reverted(
        self, mock_reference_handler
    ):
        """Test that a simple text change is not reverted by the real WikiLinkValidator."""
        mock_validator = WikiLinkValidator(reference_handler=ReferenceHandler())
        adapter = WikiLinkValidatorAdapter(mock_validator)

        original = "This is a sentence with a [[link]] and some text."
        edited = "This is a sentence with a [[link]] and some changed text."
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        result_text, should_revert = await adapter.validate(original, edited, context)

        assert not should_revert
        assert result_text == edited


class TestReferenceValidatorAdapter:
    """Test ReferenceValidatorAdapter class."""

    def test_validate_no_reversion(self):
        """Test validate when no references are removed."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_references.return_value = False
        adapter = ReferenceValidatorAdapter(mock_validator)

        original = "text with <ref>reference</ref>"
        edited = "text with <ref>reference</ref>"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        mock_validator.validate_references.assert_called_once_with(
            original_paragraph_content=original,
            edited_text_with_placeholders=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_validate_with_reversion(self):
        """Test validate when references are removed."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_references.return_value = True
        adapter = ReferenceValidatorAdapter(mock_validator)

        original = "text with <ref>reference</ref>"
        edited = "text without reference"
        context = {"paragraph_index": 1, "total_paragraphs": 3}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == original
        assert should_revert is True

    def test_get_last_failure_reason_none(self):
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = ReferenceValidatorAdapter(mock_validator)
        assert adapter.get_last_failure_reason() is None


class TestSpellingValidatorAdapter(unittest.TestCase):
    """Test SpellingValidatorAdapter class."""

    def test_validate_corrects_spelling(self):
        """Test validate corrects regional spelling differences."""
        # Arrange
        mock_validator = Mock(spec=SpellingValidator)
        mock_validator.correct_regional_spellings.return_value = "corrected colour"
        adapter = SpellingValidatorAdapter(mock_validator)

        original = "original color"
        edited = "edited color"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        self.assertEqual(result_text, "corrected colour")
        self.assertFalse(should_revert)
        mock_validator.correct_regional_spellings.assert_called_once_with(
            original_paragraph_content="original color",
            final_edited_text="edited color",
            paragraph_index=0,
            total_paragraphs=1,
        )
        self.assertIsNone(adapter.get_last_failure_reason())

    def test_validate_handles_exception(self):
        """Test validate handles exceptions by reverting."""
        # Arrange
        mock_validator = Mock(spec=SpellingValidator)
        mock_validator.correct_regional_spellings.side_effect = Exception(
            "Spelling error"
        )
        adapter = SpellingValidatorAdapter(mock_validator)

        original = "original text"
        edited = "edited text"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        self.assertEqual(result_text, original)
        self.assertTrue(should_revert)
        failure_reason = adapter.get_last_failure_reason()
        self.assertIsNotNone(failure_reason)
        assert failure_reason is not None  # Help mypy understand this is not None
        self.assertIn("failed", failure_reason)
        self.assertEqual(
            failure_reason,
            "Spelling correction failed due to an exception",
        )

    def test_get_last_failure_reason_none(self):
        mock_validator = Mock(spec=SpellingValidator)
        adapter = SpellingValidatorAdapter(mock_validator)
        self.assertIsNone(adapter.get_last_failure_reason())


class TestListMarkerValidatorAdapter:
    """Test ListMarkerValidatorAdapter class."""

    def test_validate_with_restore_original_list_markers(self):
        """Test validate when validator has restore_original_list_markers method."""
        # Arrange
        mock_validator = Mock(spec=ListMarkerValidator)
        mock_validator.validate_and_restore_list_markers.return_value = (
            "* restored text"
        )
        adapter = ListMarkerValidatorAdapter(mock_validator)

        original = "* original text"
        edited = "edited text"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == "* restored text"
        assert should_revert is False
        mock_validator.validate_and_restore_list_markers.assert_called_once_with(
            original_paragraph_content=original,
            edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_validate_with_validate_and_restore_list_markers(self):
        """Test validate when validator only has validate_and_restore_list_markers
        method."""
        # Arrange
        mock_validator = Mock(spec=ListMarkerValidator)
        # Remove the restore_original_list_markers attribute
        delattr(mock_validator, "restore_original_list_markers")
        mock_validator.validate_and_restore_list_markers.return_value = (
            "# restored text"
        )
        adapter = ListMarkerValidatorAdapter(mock_validator)

        original = "# original text"
        edited = "edited text"
        context = {"paragraph_index": 1, "total_paragraphs": 2}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == "# restored text"
        assert should_revert is False
        mock_validator.validate_and_restore_list_markers.assert_called_once_with(
            original_paragraph_content=original,
            edited_text=edited,
            paragraph_index=1,
            total_paragraphs=2,
        )

    def test_get_last_failure_reason_none(self):
        mock_validator = Mock(spec=ListMarkerValidator)
        adapter = ListMarkerValidatorAdapter(mock_validator)
        assert adapter.get_last_failure_reason() is None


class TestMetaCommentaryValidatorAdapter:
    """Test MetaCommentaryValidatorAdapter class."""

    def test_validate_no_reversion(self):
        """Test validate when meta commentary validator doesn't trigger reversion."""
        # Arrange
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )

        mock_validator = Mock(spec=MetaCommentaryValidator)
        mock_validator.validate.return_value = ("edited text", False)
        mock_validator.get_last_failure_reason.return_value = None
        adapter = MetaCommentaryValidatorAdapter(mock_validator)

        original = "original text"
        edited = "edited text"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == "edited text"
        assert should_revert is False
        mock_validator.validate.assert_called_once_with(original, edited, context)
        assert adapter.get_last_failure_reason() is None

    def test_validate_with_reversion(self):
        """Test validate when meta commentary validator triggers reversion."""
        # Arrange
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )

        mock_validator = Mock(spec=MetaCommentaryValidator)
        mock_validator.validate.return_value = ("original text", True)
        mock_validator.get_last_failure_reason.return_value = "Meta commentary detected"
        adapter = MetaCommentaryValidatorAdapter(mock_validator)

        original = "original text"
        edited = "edited text with meta commentary"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == "original text"
        assert should_revert is True
        mock_validator.validate.assert_called_once_with(original, edited, context)
        assert adapter.get_last_failure_reason() == "Meta commentary detected"

    def test_get_last_failure_reason_fallback(self):
        """Test get_last_failure_reason falls back to validator's reason."""
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )

        mock_validator = Mock(spec=MetaCommentaryValidator)
        mock_validator.get_last_failure_reason.return_value = "Validator failure reason"
        adapter = MetaCommentaryValidatorAdapter(mock_validator)

        # Ensure adapter's last_failure_reason is None
        assert adapter.last_failure_reason is None

        # Act
        result = adapter.get_last_failure_reason()

        # Assert - should return validator's reason when adapter's is None
        assert result == "Validator failure reason"

    def test_get_last_failure_reason_adapter_takes_precedence(self):
        """Test get_last_failure_reason returns adapter's reason when set."""
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )

        mock_validator = Mock(spec=MetaCommentaryValidator)
        mock_validator.get_last_failure_reason.return_value = "Validator failure reason"
        adapter = MetaCommentaryValidatorAdapter(mock_validator)

        # Set adapter's last_failure_reason
        adapter.last_failure_reason = "Adapter failure reason"

        # Act
        result = adapter.get_last_failure_reason()

        # Assert - should return adapter's reason when set
        assert result == "Adapter failure reason"


class TestReferenceContentValidatorAdapter:
    """Test ReferenceContentValidatorAdapter class."""

    def test_validate_no_content_changes(self, mock_reference_handler):
        """Test validate when reference content does not change."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_reference_content_changes.return_value = False
        adapter = ReferenceContentValidatorAdapter(
            mock_validator, mock_reference_handler
        )

        original = "text with <ref>ref</ref>"
        edited = "text with <ref>ref</ref>"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        mock_validator.validate_reference_content_changes.assert_called_once_with(
            original_paragraph_content=original,
            final_edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_validate_with_content_changes(self, mock_reference_handler):
        """Test validate when reference content changes."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_reference_content_changes.return_value = True
        adapter = ReferenceContentValidatorAdapter(
            mock_validator, mock_reference_handler
        )

        original = "text with <ref>ref</ref>"
        edited = "text with <ref>changed</ref>"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == original
        assert should_revert is True
        mock_validator.validate_reference_content_changes.assert_called_once_with(
            original_paragraph_content=original,
            final_edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_get_last_failure_reason_none(self, mock_reference_handler):
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = ReferenceContentValidatorAdapter(
            mock_validator, mock_reference_handler
        )
        assert adapter.get_last_failure_reason() is None

    def test_validate_with_placeholders_correctly_restores_references(
        self, mock_reference_handler
    ):
        """Test that validate correctly restores references from placeholders before
        validation."""
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_reference_content_changes.return_value = False
        adapter = ReferenceContentValidatorAdapter(
            mock_validator, mock_reference_handler
        )
        original = "text with {{REF_PLACEHOLDER_0}}"
        edited = "edited text with {{REF_PLACEHOLDER_0}}"
        refs_list: List[str] = ["<ref>ref</ref>"]
        context = {"refs_list": refs_list}

        # Mock restore_references to check if it's called correctly
        def restore_side_effect(text, refs):
            if "{{REF_PLACEHOLDER_0}}" in text:
                return text.replace("{{REF_PLACEHOLDER_0}}", refs[0])
            return text

        mock_reference_handler.restore_references.side_effect = restore_side_effect

        adapter.validate(original, edited, context)

        # It should be called on both the original and edited text
        assert mock_reference_handler.restore_references.call_count == 2
        mock_reference_handler.restore_references.assert_any_call(original, refs_list)
        mock_reference_handler.restore_references.assert_any_call(edited, refs_list)

        # The underlying validator should be called with the restored text
        mock_validator.validate_reference_content_changes.assert_called_once_with(
            original_paragraph_content="text with <ref>ref</ref>",
            final_edited_text="edited text with <ref>ref</ref>",
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_validate_without_placeholders_uses_original_text(
        self, mock_reference_handler
    ):
        """Test that original text is used when no placeholders are present."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_reference_content_changes.return_value = False
        adapter = ReferenceContentValidatorAdapter(
            mock_validator, mock_reference_handler
        )

        original = "text with <ref>ref</ref>"
        edited = "edited text"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert should_revert is False
        mock_reference_handler.restore_references.assert_not_called()
        mock_validator.validate_reference_content_changes.assert_called_once_with(
            original_paragraph_content=original,
            final_edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_reference_content_validator_with_failing_text_does_not_revert(
        self,
    ):
        """
        Uses text from the failing integration test to isolate the
        ReferenceContentValidatorAdapter and confirm it does not incorrectly
        revert the edit.
        """
        reference_handler = ReferenceHandler()
        validator = ReferenceValidator()
        adapter = ReferenceContentValidatorAdapter(validator, reference_handler)

        original_content = 'The FreeBSD project has stated that "a less publicized and unintended use of the GPL is that it is very favorable to large companies that want to undercut software companies. In other words, the GPL is well suited for use as a marketing weapon, potentially reducing overall economic benefit and contributing to monopolistic behavior" and that the GPL can "present a real problem for those wishing to commercialize and profit from software."<ref>{{cite web|url=http://www.freebsd.org/doc/en_US.ISO8859-1/articles/bsdl-gpl/article.html#GPL-ADVANTAGES |title=GPL Advantages and Disadvantages |publisher=FreeBSD |first=Bruce |last=Montague |date=13 November 2013 |access-date=28 November 2015}}</ref>'

        original_with_placeholders, refs_list = (
            reference_handler.replace_references_with_placeholders(original_content)
        )
        edited_with_placeholders = original_with_placeholders.replace(
            "is very favorable", "is favorable"
        )

        context = {
            "refs_list": refs_list,
            "paragraph_index": 0,
            "total_paragraphs": 1,
        }

        _, should_revert = adapter.validate(
            original_with_placeholders, edited_with_placeholders, context
        )
        assert not should_revert


class TestAddedContentValidatorAdapter:
    """Test AddedContentValidatorAdapter class."""

    def test_validate_no_added_content(self, mock_reference_handler):
        """Test validate when no new content is added."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = False
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = "text"
        edited = "edited text"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        mock_validator.validate_added_content.assert_called_once_with(
            original_paragraph_content=original,
            final_edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_validate_with_added_content(self, mock_reference_handler):
        """Test validate when new content is added."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = True
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = "text"
        edited = "edited text with [[new link]]"
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert result_text == original
        assert should_revert is True
        mock_validator.validate_added_content.assert_called_once_with(
            original_paragraph_content=original,
            final_edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_get_last_failure_reason_none(self, mock_reference_handler):
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)
        assert adapter.get_last_failure_reason() is None

    @patch("wikitextparser.parse")
    def test_determine_what_was_added_with_links(
        self, mock_parse, mock_reference_handler
    ):
        adapter = AddedContentValidatorAdapter(
            Mock(spec=ReferenceValidator), mock_reference_handler
        )
        original_parsed = Mock()
        original_parsed.wikilinks = []
        original_parsed.get_tags.return_value = []  # Need this method too

        # Create a mock wikilink with target attribute
        mock_link = Mock()
        mock_link.target = "New Link"
        edited_parsed = Mock()
        edited_parsed.wikilinks = [mock_link]
        edited_parsed.get_tags.return_value = []  # No refs

        mock_parse.side_effect = [original_parsed, edited_parsed]
        reason = adapter._determine_what_was_added("original", "edited")
        assert "New wikilinks added" in reason

    @patch("wikitextparser.parse")
    def test_determine_what_was_added_with_refs(
        self, mock_parse, mock_reference_handler
    ):
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original_parsed = Mock()
        original_parsed.wikilinks = []
        original_parsed.get_tags.return_value = []
        edited_parsed = Mock()
        edited_parsed.wikilinks = []
        edited_parsed.get_tags.return_value = ["<ref>New Ref</ref>"]
        mock_parse.side_effect = [original_parsed, edited_parsed]

        # Act
        reason = adapter._determine_what_was_added("original", "edited")

        # Assert
        assert "New reference tags added" in reason

    @patch("wikitextparser.parse")
    def test_determine_what_was_added_both(self, mock_parse, mock_reference_handler):
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original_parsed = Mock()
        original_parsed.wikilinks = []
        original_parsed.get_tags.return_value = []

        # Create a mock wikilink with target attribute
        mock_link = Mock()
        mock_link.target = "New Link"
        edited_parsed = Mock()
        edited_parsed.wikilinks = [mock_link]
        edited_parsed.get_tags.return_value = ["<ref>New Ref</ref>"]
        mock_parse.side_effect = [original_parsed, edited_parsed]

        # Act
        reason = adapter._determine_what_was_added("original", "edited")

        # Assert
        assert "New wikilinks added" in reason
        assert "New reference tags added" in reason

    @patch("wikitextparser.parse")
    def test_determine_what_was_added_no_changes(
        self, mock_parse, mock_reference_handler
    ):
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original_parsed = Mock()
        original_parsed.wikilinks = []
        original_parsed.get_tags.return_value = []
        edited_parsed = Mock()
        edited_parsed.wikilinks = []
        edited_parsed.get_tags.return_value = []
        mock_parse.side_effect = [original_parsed, edited_parsed]

        # Act
        reason = adapter._determine_what_was_added("original", "edited")

        # Assert
        assert "New content was added (could not determine specific type)" in reason

    @patch("wikitextparser.parse")
    def test_determine_what_was_added_exception(
        self, mock_parse, mock_reference_handler
    ):
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)
        mock_parse.side_effect = Exception("Parsing failed")

        # Act
        reason = adapter._determine_what_was_added("original", "edited")

        # Assert
        assert "New content was added (error analyzing changes)" in reason

    def test_validate_with_placeholders_correctly_restores_references(
        self, mock_reference_handler
    ):
        """Test that validate correctly restores references from placeholders before
        validation."""
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = False
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)
        original = "text with {{REF_PLACEHOLDER_0}}"
        edited = "edited text with {{REF_PLACEHOLDER_0}}"
        refs_list: List[str] = ["<ref>ref</ref>"]
        context = {"refs_list": refs_list}

        def restore_side_effect(text, refs):
            if "{{REF_PLACEHOLDER_0}}" in text:
                return text.replace("{{REF_PLACEHOLDER_0}}", refs[0])
            return text

        mock_reference_handler.restore_references.side_effect = restore_side_effect

        adapter.validate(original, edited, context)

        assert mock_reference_handler.restore_references.call_count == 2
        mock_reference_handler.restore_references.assert_any_call(original, refs_list)
        mock_reference_handler.restore_references.assert_any_call(edited, refs_list)

        mock_validator.validate_added_content.assert_called_once_with(
            original_paragraph_content="text with <ref>ref</ref>",
            final_edited_text="edited text with <ref>ref</ref>",
            paragraph_index=0,
            total_paragraphs=1,
        )

    def test_validate_with_prefix_added_should_not_flag_as_new_content(self):
        """Test that adding a prefix to the text doesn't incorrectly flag the
        content as new."""
        # Arrange
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = False  # No content added
        mock_reference_handler = Mock()
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = "The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation."
        edited = "Edited: The text of the GPL is itself [[copyright]]ed, and the copyright is held by the Free Software Foundation."
        context = {"paragraph_index": 0, "total_paragraphs": 1}

        # Act
        result_text, should_revert = adapter.validate(original, edited, context)

        # Assert
        assert should_revert is False, "Should not revert when only a prefix is added"
        assert result_text == edited
        mock_validator.validate_added_content.assert_called_once_with(
            original_paragraph_content=original,
            final_edited_text=edited,
            paragraph_index=0,
            total_paragraphs=1,
        )


class TestAddedContentValidatorAdapterCaseChanges:
    """Test case changes in AddedContentValidatorAdapter."""

    def test_validate_link_case_change_not_reverted(self, mock_reference_handler):
        """Test that case changes in wikilinks are not reverted."""
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = (
            False  # No reversion needed
        )
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = "Link to [[Apple]]"
        edited = "Link to [[apple]]"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        result_text, should_revert = adapter.validate(original, edited, context)
        assert not should_revert
        assert result_text == edited

    def test_validate_multiple_case_changes_not_reverted(self, mock_reference_handler):
        """Test that multiple case changes in wikilinks are not reverted."""
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = (
            False  # No reversion needed
        )
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = "Links to [[Apple]], [[Banana]], and [[Cherry]]"
        edited = "Links to [[apple]], [[banana]], and [[cherry]]"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        result_text, should_revert = adapter.validate(original, edited, context)
        assert not should_revert
        assert result_text == edited

    def test_validate_actual_addition_still_reverted(self, mock_reference_handler):
        """Test that a genuine addition is still reverted."""
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = True  # Reversion needed
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = "Link to [[Apple]]"
        edited = "Link to [[Apple]] and [[Orange]]"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        result_text, should_revert = adapter.validate(original, edited, context)
        assert should_revert
        assert result_text == original

    def test_validate_fruit_tree_case_change_scenario(self, mock_reference_handler):
        """Test a specific scenario from the examples with case change."""
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = (
            False  # No reversion needed
        )
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original = (
            "The [[apple tree]] is a [[deciduous tree]] in the [[rose family]]..."
        )
        edited = "The [[Apple tree]] is a [[deciduous tree]] in the [[rose family]]..."
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        result_text, should_revert = adapter.validate(original, edited, context)
        assert not should_revert
        assert result_text == edited


class TestCompositeReferenceValidatorAdapter(unittest.TestCase):
    """Test CompositeReferenceValidatorAdapter class."""

    def setUp(self):
        """Set up the tests."""
        self.mock_validator = MagicMock(spec=ReferenceValidator)
        self.mock_reversion_tracker = MagicMock()
        self.adapter = CompositeReferenceValidatorAdapter(
            self.mock_validator, self.mock_reversion_tracker
        )

    def test_validate_no_placeholders(self):
        """Test validate when text has no reference placeholders."""
        # Arrange
        original = "text without references"
        edited = "edited text without references"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        # Act
        result_text, should_revert = self.adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        self.mock_validator.validate_references.assert_not_called()

    def test_validate_with_none_refs_list(self):
        """Test validate when refs_list is None - this would cause TypeError without the fix."""
        # Arrange
        original = "text without references"
        edited = "edited text with 0 placeholder"  # Contains a placeholder pattern
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": None}

        # Act - this would throw TypeError: object of type 'NoneType' has no len() without the fix
        result_text, should_revert = self.adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        self.mock_validator.validate_references.assert_not_called()

    def test_validate_with_none_refs_list_and_multiple_placeholders(self):
        """Test validate when refs_list is None and edited text has multiple placeholder patterns."""
        # Arrange
        original = "text without references"
        edited = "edited text with 0 and 1 and 2 placeholders"  # Multiple placeholder patterns
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": None}

        # Act - this would throw TypeError without the fix
        result_text, should_revert = self.adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        self.mock_validator.validate_references.assert_not_called()

    def test_validate_with_empty_refs_list_still_works(self):
        """Test validate when refs_list is empty list (should work both before and after fix)."""
        # Arrange
        original = "text without references"
        edited = "edited text with 0 placeholder"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": []}

        # Act
        result_text, should_revert = self.adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        self.mock_validator.validate_references.assert_not_called()

    def test_validate_with_placeholders_no_reversion(self):
        """Test validate with placeholders when validation passes."""
        # Arrange
        original = 'text with <ref name="test">a reference</ref>'
        edited = "text with 0"
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": ["ref1"]}

        # Act
        result_text, should_revert = self.adapter.validate(original, edited, context)

        # Assert
        assert result_text == edited
        assert should_revert is False
        self.mock_reversion_tracker.record_reversion.assert_not_called()

    def test_validate_with_placeholders_and_reversion(self):
        """Test validate with placeholders when validation fails."""
        # Arrange
        original = 'text with <ref name="test">a reference</ref>'
        edited = 'text with <ref name="0" />'
        context = {"paragraph_index": 0, "total_paragraphs": 1, "refs_list": ["ref1"]}

        # Act
        result_text, should_revert = self.adapter.validate(original, edited, context)

        # Assert
        assert result_text == original
        assert should_revert is True
        self.mock_reversion_tracker.record_reversion.assert_called_once_with(
            ReversionType.REFERENCE_VALIDATION_FAILURE
        )

    def test_determine_reference_failure_reason_all_removed(self):
        """Test _determine_reference_failure_reason when all references are removed."""
        original = "<ref>ref1</ref>"
        edited = "content with no placeholders"
        refs_list: List[str] = []  # Empty refs list so no  patterns match

        from unittest.mock import patch

        with patch.object(
            self.adapter.reference_validator,
            "_extract_reference_placeholders",
            return_value={"0": ""},
        ):
            reason = self.adapter._determine_reference_failure_reason(
                original, edited, refs_list
            )
        assert reason == "All references were removed from the text"

    def test_determine_reference_failure_reason_corrupted(self):
        """Test _determine_reference_failure_reason when placeholders are corrupted."""
        original = "<ref>ref1</ref>"
        edited = 'content with <ref name="0" />'  # 1 placeholder, 1 original ref
        refs_list: List[str] = ["ref1"]  # 1 ref in list

        from unittest.mock import patch

        with patch.object(
            self.adapter.reference_validator,
            "_extract_reference_placeholders",
            return_value={"0": ""},
        ):
            reason = self.adapter._determine_reference_failure_reason(
                original, edited, refs_list
            )
        assert reason == "Reference placeholders were modified or corrupted"

    def test_determine_reference_failure_reason_missing_count(self):
        """Test _determine_reference_failure_reason when some references are missing."""
        original = "<ref>ref1</ref><ref>ref2</ref>"  # 2 refs
        edited = 'content with <ref name="0" />'  # 1 placeholder
        refs_list: List[str] = ["ref1", "ref2"]  # 2 refs in list

        from unittest.mock import patch

        with patch.object(
            self.adapter.reference_validator,
            "_extract_reference_placeholders",
            return_value={"0": "", "1": ""},
        ):
            reason = self.adapter._determine_reference_failure_reason(
                original, edited, refs_list
            )
        assert "1 reference(s) were removed from the text" in (reason or "")

    def test_determine_reference_failure_reason_exception(self):
        """Test _determine_reference_failure_reason exception handling."""
        # Test: Exception handling by passing invalid data that causes an error
        # We'll patch the range function to raise an exception
        with patch("builtins.range", side_effect=Exception("Test exception")):
            reason = self.adapter._determine_reference_failure_reason(
                "original", "edited", ["ref1"]
            )
            assert (
                reason
                == "Reference validation failed (unable to determine specific cause)"
            )

    def test_get_last_failure_reason_none(self):
        assert self.adapter.get_last_failure_reason() is None

    def test_no_refs_list(self):
        context = {"paragraph_index": 0, "total_paragraphs": 1}
        # Ensure refs_list is always a list, not None
        refs_list: List[str] = []
        context_with_refs = dict(context)
        context_with_refs["refs_list"] = refs_list  # type: ignore
        result_text, should_revert = self.adapter.validate(
            "original", "edited", context_with_refs
        )
        assert result_text == "edited"
        assert should_revert is False


# Integration tests from test_integration_reference_validation.py
"""
Integration tests for reference content validation.

This module tests that reference content validation works correctly
when references are replaced with placeholders and then restored.
"""

# Import helper function
replace_references_with_placeholders = (
    ReferenceHandler.replace_references_with_placeholders
)


class TestReferenceValidationIntegration:
    """Integration tests for reference validation with placeholders."""

    def test_reference_content_validation_with_unchanged_references(
        self, mock_reference_handler
    ):
        """Test that unchanged references pass content validation."""
        # Use a mock validator instead of real one to control the behavior
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_reference_content_changes.return_value = False
        adapter = ReferenceContentValidatorAdapter(
            mock_validator, mock_reference_handler
        )

        original_text = "This paragraph has <ref>a reference</ref>."
        edited_text_with_placeholders = "This paragraph has been edited but retains 0."

        context = {
            "paragraph_index": 0,
            "total_paragraphs": 1,
            "refs_list": ["<ref>a reference</ref>"],
        }

        result_text, should_revert = adapter.validate(
            original_text, edited_text_with_placeholders, context
        )

        assert not should_revert
        assert result_text == edited_text_with_placeholders

    def test_reference_content_validation_with_actually_changed_references(
        self, mock_reference_handler
    ):
        """Test that changed references fail content validation."""
        validator = ReferenceValidator()
        adapter = ReferenceContentValidatorAdapter(validator, mock_reference_handler)

        original_text = "This paragraph has <ref>an original reference</ref>."
        text_with_placeholders, refs_list = (
            mock_reference_handler.replace_references_with_placeholders(original_text)
        )
        edited_text_with_placeholders = (
            "This paragraph has been edited and the reference 0 was changed."
        )

        context = {
            "paragraph_index": 0,
            "total_paragraphs": 1,
            "refs_list": refs_list,  # Original refs list
        }

        # Restore with *different* content
        restored_text = "This paragraph has been edited and the reference <ref>a changed reference</ref> was changed."
        mock_reference_handler.restore_references.return_value = restored_text

        result_text, should_revert = adapter.validate(
            original_text, edited_text_with_placeholders, context
        )

        assert should_revert
        assert result_text == original_text

    def test_added_content_validation_with_unchanged_content_via_placeholders(
        self, mock_reference_handler
    ):
        """Test that unchanged content (with placeholders) passes added content
        validation."""
        validator = ReferenceValidator()
        adapter = AddedContentValidatorAdapter(validator, mock_reference_handler)

        original_text = "This text has <ref>a reference</ref>."
        text_with_placeholders, refs_list = (
            mock_reference_handler.replace_references_with_placeholders(original_text)
        )

        # Pretend the LLM returns the same placeholder
        edited_text_with_placeholders = text_with_placeholders

        context = {
            "paragraph_index": 0,
            "total_paragraphs": 1,
            "refs_list": refs_list,
        }

        # Restore placeholder for validation
        mock_reference_handler.restore_references.return_value = original_text

        result_text, should_revert = adapter.validate(
            original_text, edited_text_with_placeholders, context
        )

        assert not should_revert

    def test_added_content_validation_detects_actual_new_content(
        self, mock_reference_handler
    ):
        """Test that new content (even with placeholders) is detected."""
        # Use a mock validator that detects the new content
        mock_validator = Mock(spec=ReferenceValidator)
        mock_validator.validate_added_content.return_value = True
        adapter = AddedContentValidatorAdapter(mock_validator, mock_reference_handler)

        original_text = "This text has <ref>a reference</ref>."
        edited_text_with_placeholders = "This text has some new content and 0"

        context = {
            "paragraph_index": 0,
            "total_paragraphs": 1,
            "refs_list": ["<ref>a reference</ref>"],
        }

        result_text, should_revert = adapter.validate(
            original_text, edited_text_with_placeholders, context
        )

        assert should_revert

    def test_validation_context_flow_matches_rejected_edit_log_examples(
        self, mock_reference_handler
    ):
        """Test that the validation flow correctly identifies and logs rejected edits
        based on examples."""
        validator = ReferenceValidator()
        ref_content_adapter = ReferenceContentValidatorAdapter(
            validator, mock_reference_handler
        )
        AddedContentValidatorAdapter(validator, mock_reference_handler)

        original_text = "The [[apple tree]] is a [[deciduous tree]].<ref>source A</ref>"
        text_with_placeholders, refs_list = (
            mock_reference_handler.replace_references_with_placeholders(original_text)
        )

        # Scenario 1: Reference content change
        edited_placeholder_1 = "The [[apple tree]] is a [[deciduous tree]].0"
        restored_text_1 = (
            "The [[apple tree]] is a [[deciduous tree]].<ref>source B</ref>"
        )
        mock_reference_handler.restore_references.return_value = restored_text_1

        context = {
            "paragraph_index": 0,
            "total_paragraphs": 1,
            "refs_list": refs_list,
        }

        result_text, should_revert = ref_content_adapter.validate(
            original_text, edited_placeholder_1, context
        )

        assert should_revert
        failure_reason = ref_content_adapter.get_last_failure_reason()
        assert failure_reason is not None
        assert "Reference content was modified" in failure_reason


class TestTemplateValidatorAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_validator = MagicMock(spec=TemplateValidator)
        self.mock_reference_handler = MagicMock(spec=IReferenceHandler)
        self.adapter = TemplateValidatorAdapter(
            self.mock_validator, self.mock_reference_handler
        )

    def test_validate_restores_references_before_validation(self):
        """Test that the adapter restores references before calling the validator."""
        original = "original with placeholder"
        edited = "edited with placeholder"
        context = {"refs_list": ["<ref>some ref</ref>"]}
        self.mock_reference_handler.restore_references.side_effect = [
            "original with ref",
            "edited with ref",
        ]
        self.mock_validator.validate.return_value = False

        result_text, should_revert = self.adapter.validate(original, edited, context)

        self.mock_reference_handler.restore_references.assert_any_call(
            original, context["refs_list"]
        )
        self.mock_reference_handler.restore_references.assert_any_call(
            edited, context["refs_list"]
        )
        self.mock_validator.validate.assert_called_once_with(
            original_text="original with ref",
            edited_text="edited with ref",
            paragraph_index=0,
            total_paragraphs=1,
        )
        self.assertFalse(should_revert)
        self.assertEqual(edited, result_text)

    def test_revert_path(self):
        self.mock_validator.validate.return_value = True
        _, should_revert = self.adapter.validate("original", "edited", {})
        self.assertTrue(should_revert)
        failure_reason = self.adapter.get_last_failure_reason()
        self.assertIsNotNone(failure_reason)
        assert failure_reason is not None  # Help mypy understand this is not None
        self.assertIn("templates were removed", str(failure_reason))


class TestQuoteValidatorAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_validator = MagicMock(spec=QuoteValidator)
        self.mock_reference_handler = MagicMock(spec=IReferenceHandler)
        self.adapter = QuoteValidatorAdapter(
            self.mock_validator, self.mock_reference_handler
        )

    def test_validate_restores_references_before_validation(self):
        # Arrange
        self.mock_validator.validate_and_correct.return_value = (
            "edited with refs",
            False,
        )
        self.mock_reference_handler.restore_references.side_effect = [
            "original with refs",
            "edited with refs",
        ]
        self.mock_reference_handler.replace_references_with_placeholders.return_value = (
            "corrected with placeholders",
            [],
        )
        original = "original with placeholders"
        edited = "edited with placeholders"
        context = {"refs_list": ["<ref>..."]}

        # Act
        self.adapter.validate(original, edited, context)

        # Assert
        self.mock_reference_handler.restore_references.assert_any_call(
            original, context["refs_list"]
        )
        self.mock_reference_handler.restore_references.assert_any_call(
            edited, context["refs_list"]
        )
        self.mock_validator.validate_and_correct.assert_called_once()

    def test_revert_path(self):
        self.mock_validator.validate_and_correct.return_value = ("original", True)
        original = "original"
        edited = "edited"
        context: dict = {"refs_list": []}
        result, revert = self.adapter.validate(original, edited, context)
        self.assertTrue(revert)
        self.assertEqual(result, original)
        failure_reason = self.adapter.get_last_failure_reason()
        self.assertIsNotNone(failure_reason)
        assert failure_reason is not None  # Help mypy understand this is not None
        self.assertIn("could not be automatically corrected", failure_reason)
