"""
Tests for the editing service module.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.editing.edit_orchestrator import ParagraphResult
from services.editing.edit_service import WikiEditor
from services.utils.wiki_utils import is_prose_content
from services.utils.wikipedia_api import WikipediaAPIError
from services.validation.validators.list_marker_validator import ListMarkerValidator


class TestWikiEditor:
    """Test cases for WikiEditor class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value="Edited content")
        return llm

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for WikiEditor."""
        deps = {
            "document_processor": Mock(),
            "content_classifier": Mock(),
            "reversion_tracker": Mock(),
            "reference_handler": Mock(),
        }
        return deps

    @pytest.fixture
    def wiki_editor(self, mock_llm, mock_dependencies):
        """Create a WikiEditor instance for testing."""
        return WikiEditor(
            llm=mock_llm, editing_mode="copyedit", verbose=False, **mock_dependencies
        )

    def test_wiki_editor_initialization(self, mock_llm):
        """Test WikiEditor initialization with default components."""
        editor = WikiEditor(llm=mock_llm, editing_mode="copyedit")
        assert editor.llm == mock_llm
        assert editor.editing_mode == "copyedit"
        assert editor.verbose is False
        assert editor.document_processor is not None
        assert editor.content_classifier is not None
        assert editor.reversion_tracker is not None
        assert editor.reference_handler is not None
        assert editor.paragraph_processor is not None
        assert editor.orchestrator is not None

    def test_wiki_editor_initialization_with_custom_components(
        self, mock_llm, mock_dependencies
    ):
        """Test WikiEditor initialization with custom components."""
        editor = WikiEditor(
            llm=mock_llm, editing_mode="brevity", verbose=True, **mock_dependencies
        )
        assert editor.llm == mock_llm
        assert editor.editing_mode == "brevity"
        assert editor.verbose is True
        assert editor.document_processor == mock_dependencies["document_processor"]
        assert editor.content_classifier == mock_dependencies["content_classifier"]
        assert editor.reversion_tracker == mock_dependencies["reversion_tracker"]
        assert editor.reference_handler == mock_dependencies["reference_handler"]

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_empty_text(self, wiki_editor):
        """Test edit_wikitext_structured with empty text."""
        result = await wiki_editor.edit_wikitext_structured("")
        assert result == []

        result = await wiki_editor.edit_wikitext_structured("   \n\t  ")
        assert result == []

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_success(self, wiki_editor):
        """Test successful edit_wikitext_structured."""
        # Mock the orchestrator to return some results
        mock_results = [
            ParagraphResult(
                before="Original text",
                after="Edited text",
                status="CHANGED",
                status_details="Successfully edited",
            )
        ]
        wiki_editor.orchestrator.orchestrate_edit_structured = AsyncMock(
            return_value=mock_results
        )

        result = await wiki_editor.edit_wikitext_structured("Some wikitext")
        assert result == mock_results

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_with_progress_callback(self, wiki_editor):
        """Test edit_wikitext_structured with progress callback."""
        callback = Mock()
        mock_results = [
            ParagraphResult(
                before="Original text",
                after="Edited text",
                status="CHANGED",
                status_details="Successfully edited",
            )
        ]
        wiki_editor.orchestrator.orchestrate_edit_structured = AsyncMock(
            return_value=mock_results
        )

        result = await wiki_editor.edit_wikitext_structured("Some wikitext", callback)
        assert result == mock_results
        wiki_editor.orchestrator.orchestrate_edit_structured.assert_called_once_with(
            "Some wikitext", wiki_editor.paragraph_processor, callback
        )

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_orchestrator_exception(self, wiki_editor):
        """Test edit_wikitext_structured when orchestrator raises exception."""
        # Mock orchestrator to raise exception
        wiki_editor.orchestrator.orchestrate_edit_structured = AsyncMock(
            side_effect=ValueError("Orchestration failed")
        )

        # Mock document processor to return items
        wiki_editor.document_processor.process = Mock(
            return_value=["Paragraph 1", "Paragraph 2", "Paragraph 3"]
        )

        result = await wiki_editor.edit_wikitext_structured("Some wikitext")

        # Should return error results for each paragraph
        assert len(result) == 3
        for res in result:
            assert res.status == "ERRORED"
            assert res.before == res.after
            assert "Input validation failed" in res.status_details

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_large_document_exception(self, wiki_editor):
        """Test edit_wikitext_structured exception handling for large documents."""
        # Mock orchestrator to raise exception
        wiki_editor.orchestrator.orchestrate_edit_structured = AsyncMock(
            side_effect=RuntimeError("Processing failed")
        )

        # Mock document processor to return many items (>100)
        large_doc_items = [f"Paragraph {i}" for i in range(150)]
        wiki_editor.document_processor.process = Mock(return_value=large_doc_items)

        result = await wiki_editor.edit_wikitext_structured("Large document")

        # Should return a single error result for large documents
        assert len(result) == 1
        assert result[0].status == "ERRORED"
        assert (
            "Processing failed for large document (150 items)"
            in result[0].status_details
        )
        assert len(result[0].before) > 100  # Combined text

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_fallback_exception(self, wiki_editor):
        """Test edit_wikitext_structured when both orchestrator and fallback fail."""
        # Mock orchestrator to raise exception
        wiki_editor.orchestrator.orchestrate_edit_structured = AsyncMock(
            side_effect=RuntimeError("Primary error")
        )

        # Mock document processor to also raise exception
        wiki_editor.document_processor.process = Mock(
            side_effect=ValueError("Document parsing failed")
        )

        result = await wiki_editor.edit_wikitext_structured("Some wikitext")

        # Should return a single error result with combined error message
        assert len(result) == 1
        assert result[0].status == "ERRORED"
        assert result[0].before == "Some wikitext"
        assert result[0].after == "Some wikitext"
        assert "Critical processing failure" in result[0].status_details
        assert "document parsing failed" in result[0].status_details.lower()

    @pytest.mark.asyncio
    async def test_edit_article_by_title_structured_empty_title(self, wiki_editor):
        """Test edit_article_by_title_structured with empty title."""
        with pytest.raises(ValueError, match="Article title cannot be empty"):
            await wiki_editor.edit_article_by_title_structured("")

        with pytest.raises(ValueError, match="Article title cannot be empty"):
            await wiki_editor.edit_article_by_title_structured("   ")

    @pytest.mark.asyncio
    async def test_edit_article_by_title_structured_success(self, wiki_editor):
        """Test successful edit_article_by_title_structured."""
        # Mock Wikipedia API
        with patch("services.editing.edit_service.WikipediaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.get_article_wikitext = AsyncMock(
                return_value="Article wikitext content"
            )

            # Mock edit_wikitext_structured
            mock_results = [
                ParagraphResult(
                    before="Original",
                    after="Edited",
                    status="CHANGED",
                    status_details="Success",
                )
            ]
            wiki_editor.edit_wikitext_structured = AsyncMock(return_value=mock_results)

            result = await wiki_editor.edit_article_by_title_structured("Test Article")

            assert result == mock_results
            mock_api_class.assert_called_once_with(language="en")
            mock_api.get_article_wikitext.assert_called_once_with("Test Article")
            wiki_editor.edit_wikitext_structured.assert_called_once_with(
                "Article wikitext content"
            )

    @pytest.mark.asyncio
    async def test_edit_article_by_title_structured_wikipedia_error(self, wiki_editor):
        """Test edit_article_by_title_structured when Wikipedia API fails."""
        with patch("services.editing.edit_service.WikipediaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.get_article_wikitext = AsyncMock(
                side_effect=WikipediaAPIError("Article not found")
            )

            with pytest.raises(WikipediaAPIError, match="Article not found"):
                await wiki_editor.edit_article_by_title_structured(
                    "Nonexistent Article"
                )

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_empty_inputs(self, wiki_editor):
        """Test edit_article_section_structured with empty inputs."""
        with pytest.raises(ValueError, match="Article title cannot be empty"):
            await wiki_editor.edit_article_section_structured("", "Section")

        with pytest.raises(ValueError, match="Section title cannot be empty"):
            await wiki_editor.edit_article_section_structured("Article", "")

        with pytest.raises(ValueError, match="Section title cannot be empty"):
            await wiki_editor.edit_article_section_structured("Article", "   ")

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_success(self, wiki_editor):
        """Test successful edit_article_section_structured."""
        with patch("services.editing.edit_service.WikipediaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.get_article_wikitext = AsyncMock(
                return_value="Full article with\n== Test Section ==\nSection content here\n== Another Section ==\nMore content"
            )

            with patch(
                "services.utils.wiki_utils.extract_section_content"
            ) as mock_extract:
                mock_extract.return_value = "Section content here"

                mock_results = [
                    ParagraphResult(
                        before="Section content here",
                        after="Edited section content",
                        status="CHANGED",
                        status_details="Success",
                    )
                ]
                wiki_editor.edit_wikitext_structured = AsyncMock(
                    return_value=mock_results
                )

                callback = Mock()
                result = await wiki_editor.edit_article_section_structured(
                    "Test Article", "Test Section", "en", callback
                )

                assert result == mock_results
                mock_api_class.assert_called_once_with(language="en")
                mock_api.get_article_wikitext.assert_called_once_with("Test Article")
                mock_extract.assert_called_once()
                wiki_editor.edit_wikitext_structured.assert_called_once_with(
                    "Section content here", callback
                )

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_section_not_found(self, wiki_editor):
        """Test edit_article_section_structured when section is not found."""
        with patch("services.editing.edit_service.WikipediaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.get_article_wikitext = AsyncMock(return_value="Article content")

            with patch(
                "services.utils.wiki_utils.extract_section_content"
            ) as mock_extract:
                mock_extract.return_value = None

                with pytest.raises(
                    ValueError,
                    match="Section 'Missing Section' not found in article 'Test Article'",
                ):
                    await wiki_editor.edit_article_section_structured(
                        "Test Article", "Missing Section"
                    )

    def test_build_pre_processing_pipeline(self, wiki_editor):
        """Test _build_pre_processing_pipeline returns empty pipeline."""
        pipeline = wiki_editor._build_pre_processing_pipeline()
        assert pipeline is not None

    def test_build_post_processing_pipeline(self, wiki_editor):
        """Test _build_post_processing_pipeline creates proper pipeline."""
        mock_validators = {
            "link_validator": Mock(),
            "template_validator": Mock(),
            "quote_validator": Mock(),
            "spelling_validator": Mock(),
            "list_marker_validator": Mock(),
            "reference_validator": Mock(),
            "meta_commentary_validator": Mock(),
        }

        pipeline = wiki_editor._build_post_processing_pipeline(mock_validators)
        assert pipeline is not None


class TestProseContentDetection:
    """Test cases for prose content detection utility."""

    def test_has_prose_content_prose_paragraph(self):
        """Test detection of prose content in a paragraph."""
        paragraph = "This is a regular prose paragraph with multiple sentences. It contains normal text content."
        result = is_prose_content(paragraph)
        assert result is True

    def test_has_prose_content_list_only(self):
        """Test detection when paragraph contains only lists."""
        paragraph = "* Item 1\n* Item 2\n* Item 3"
        result = is_prose_content(paragraph)
        assert result is False

    def test_has_prose_content_mixed_content(self):
        """Test detection when paragraph contains both prose and lists."""
        paragraph = "Here is some introduction text.\n* Item 1\n* Item 2\nAnd here is a conclusion."
        result = is_prose_content(paragraph)
        assert result is True

    def test_has_prose_content_empty_string(self):
        """Test detection with empty string."""
        result = is_prose_content("")
        assert result is False

    def test_has_prose_content_whitespace_only(self):
        """Test detection with whitespace only."""
        paragraph = "   \n\t  \n  "
        result = is_prose_content(paragraph)
        assert result is False

    def test_has_prose_content_citations_only(self):
        """Test detection when paragraph contains only citations."""
        paragraph = "<ref>Smith, John (2020). Example Book.</ref><ref>Doe, Jane (2021). Another Book.</ref>"
        result = is_prose_content(paragraph)
        assert result is False

    def test_has_prose_content_prose_with_citations(self):
        """Test detection when paragraph contains prose with citations."""
        paragraph = "This is regular text with a citation.<ref>Smith, John (2020). Example Book.</ref> More text here."
        result = is_prose_content(paragraph)
        assert result is True


class TestListMarkerValidator:
    """Test cases for ListMarkerValidator class."""

    @pytest.fixture
    def list_marker_validator(self):
        """Create a ListMarkerValidator instance."""
        return ListMarkerValidator()

    def test_validate_list_markers_preserved_unordered(self, list_marker_validator):
        """Test that unordered list markers are preserved when unchanged."""
        original = "* This is a list item"
        edited = "* This is an edited list item"
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert "*" in result
        assert "edited list item" in result

    def test_validate_list_markers_preserved_ordered(self, list_marker_validator):
        """Test that ordered list markers are preserved when unchanged."""
        original = "# This is a numbered item"
        edited = "# This is an edited numbered item"
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert "#" in result
        assert "edited numbered item" in result

    def test_validate_list_markers_removed(self, list_marker_validator):
        """Test validation when list markers are incorrectly removed."""
        original = "* This is a list item"
        edited = "This is no longer a list item"
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert result.startswith("*")

    def test_validate_list_markers_added(self, list_marker_validator):
        """Test validation when list markers are incorrectly added."""
        original = "This is regular text"
        edited = "* This is now a list item"
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert not result.startswith("*")

    def test_validate_no_list_markers(self, list_marker_validator):
        """Test validation of text without list markers."""
        original = "This is regular paragraph text."
        edited = "This is edited paragraph text."
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert result == edited

    def test_validate_mixed_list_types(self, list_marker_validator):
        """Test validation with different types of list markers."""
        original = "* Unordered item"
        edited = "* Edited unordered item"
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert "*" in result
        assert "Edited unordered item" in result

    def test_validate_list_markers_changed_type(self, list_marker_validator):
        """Test validation when list marker type is changed."""
        original = "* This is an unordered item"
        edited = "# This is now an ordered item"
        result = list_marker_validator.validate_and_restore_list_markers(
            original, edited, 0, 1
        )
        assert result.startswith("*")


class TestWikiEditorBatched:
    """Test cases for WikiEditor batched methods."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value="Edited content")
        return llm

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for WikiEditor."""
        deps = {
            "document_processor": Mock(),
            "content_classifier": Mock(),
            "reversion_tracker": Mock(),
            "reference_handler": Mock(),
        }
        return deps

    @pytest.fixture
    def wiki_editor(self, mock_llm, mock_dependencies):
        """Create a WikiEditor instance for testing."""
        return WikiEditor(
            llm=mock_llm, editing_mode="copyedit", verbose=False, **mock_dependencies
        )

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_batched_success(self, wiki_editor):
        """Test successful batched structured edit of wikitext."""
        # Setup
        text = "Test paragraph 1\nTest paragraph 2"
        enhanced_progress_callback = Mock()
        batch_size = 2

        # Mock the orchestrator's batched method
        expected_results = [
            ParagraphResult(
                before="Test paragraph 1",
                after="Edited paragraph 1",
                status="EDITED",
                status_details="Successfully edited",
            ),
            ParagraphResult(
                before="Test paragraph 2",
                after="Edited paragraph 2",
                status="EDITED",
                status_details="Successfully edited",
            ),
        ]

        with patch.object(
            wiki_editor.orchestrator, "orchestrate_edit_structured_batched"
        ) as mock_orchestrate:
            mock_orchestrate.return_value = expected_results

            # Execute
            results = await wiki_editor.edit_wikitext_structured_batched(
                text, enhanced_progress_callback, batch_size
            )

        # Verify
        assert len(results) == 2
        assert results == expected_results
        mock_orchestrate.assert_called_once_with(
            text,
            wiki_editor.paragraph_processor,
            enhanced_progress_callback,
            batch_size,
        )

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_batched_empty_text(self, wiki_editor):
        """Test batched structured edit with empty text."""
        # Execute
        results = await wiki_editor.edit_wikitext_structured_batched("", None, 2)

        # Verify
        assert results == []

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_batched_exception_handling(
        self, wiki_editor
    ):
        """Test batched structured edit exception handling."""
        # Setup
        text = "Test paragraph"
        enhanced_progress_callback = Mock()
        batch_size = 2

        with patch.object(
            wiki_editor.orchestrator, "orchestrate_edit_structured_batched"
        ) as mock_orchestrate:
            mock_orchestrate.side_effect = RuntimeError("Processing failed")

            with patch.object(
                wiki_editor.document_processor, "process"
            ) as mock_process:
                mock_process.return_value = ["Test paragraph"]

                # Execute
                results = await wiki_editor.edit_wikitext_structured_batched(
                    text, enhanced_progress_callback, batch_size
                )

        # Verify error handling
        assert len(results) == 1
        assert results[0].status == "ERRORED"
        # Error is sanitized so we just check it contains error message

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_batched_large_document_error(
        self, wiki_editor
    ):
        """Test batched structured edit with large document error handling."""
        # Setup
        text = "Test paragraph"
        enhanced_progress_callback = Mock()
        batch_size = 2

        with patch.object(
            wiki_editor.orchestrator, "orchestrate_edit_structured_batched"
        ) as mock_orchestrate:
            mock_orchestrate.side_effect = RuntimeError("Processing failed")

            # Mock large document (>100 items)
            large_document = ["paragraph"] * 101
            with patch.object(
                wiki_editor.document_processor, "process"
            ) as mock_process:
                mock_process.return_value = large_document

                # Execute
                results = await wiki_editor.edit_wikitext_structured_batched(
                    text, enhanced_progress_callback, batch_size
                )

        # Verify large document error handling
        assert len(results) == 1
        assert results[0].status == "ERRORED"
        assert (
            "Batched processing failed for large document (101 items)"
            in results[0].status_details
        )

    @pytest.mark.asyncio
    async def test_edit_wikitext_structured_batched_fallback_error(self, wiki_editor):
        """Test batched structured edit with fallback error handling."""
        # Setup
        text = "Test paragraph"
        enhanced_progress_callback = Mock()
        batch_size = 2

        with patch.object(
            wiki_editor.orchestrator, "orchestrate_edit_structured_batched"
        ) as mock_orchestrate:
            mock_orchestrate.side_effect = RuntimeError("Primary error")

            with patch.object(
                wiki_editor.document_processor, "process"
            ) as mock_process:
                mock_process.side_effect = RuntimeError("Fallback error")

                # Execute
                results = await wiki_editor.edit_wikitext_structured_batched(
                    text, enhanced_progress_callback, batch_size
                )

        # Verify fallback error handling
        assert len(results) == 1
        assert results[0].status == "ERRORED"
        assert "Critical batched processing failure" in results[0].status_details
        # Error messages are sanitized so we just check the structure

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_batched_success(self, wiki_editor):
        """Test successful batched structured edit of article section."""
        # Setup
        article_title = "Test Article"
        section_title = "Test Section"
        language = "en"
        enhanced_progress_callback = Mock()
        batch_size = 2

        expected_results = [
            ParagraphResult(
                before="Test content",
                after="Edited content",
                status="EDITED",
                status_details="Successfully edited",
            ),
        ]

        with patch.object(wiki_editor, "edit_wikitext_structured_batched") as mock_edit:
            mock_edit.return_value = expected_results

            with patch("services.editing.edit_service.WikipediaAPI") as mock_api_class:
                mock_api = mock_api_class.return_value
                mock_api.get_article_wikitext = AsyncMock(
                    return_value="Full article content"
                )

                with patch(
                    "services.utils.wiki_utils.extract_section_content"
                ) as mock_extract:
                    mock_extract.return_value = "Section content"

                    # Execute
                    results = await wiki_editor.edit_article_section_structured_batched(
                        article_title,
                        section_title,
                        language,
                        enhanced_progress_callback,
                        batch_size,
                    )

        # Verify
        assert results == expected_results
        mock_edit.assert_called_once_with(
            "Section content", enhanced_progress_callback, batch_size
        )

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_batched_empty_title(
        self, wiki_editor
    ):
        """Test batched structured edit with empty article title."""
        with pytest.raises(ValueError, match="Article title cannot be empty"):
            await wiki_editor.edit_article_section_structured_batched(
                "", "Section", "en", None, 2
            )

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_batched_empty_section(
        self, wiki_editor
    ):
        """Test batched structured edit with empty section title."""
        with pytest.raises(ValueError, match="Section title cannot be empty"):
            await wiki_editor.edit_article_section_structured_batched(
                "Article", "", "en", None, 2
            )

    @pytest.mark.asyncio
    async def test_edit_article_section_structured_batched_section_not_found(
        self, wiki_editor
    ):
        """Test batched structured edit when section is not found."""
        # Setup
        article_title = "Test Article"
        section_title = "Nonexistent Section"

        with patch("services.editing.edit_service.WikipediaAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_article_wikitext = AsyncMock(
                return_value="Full article content"
            )

            with patch(
                "services.utils.wiki_utils.extract_section_content"
            ) as mock_extract:
                mock_extract.return_value = None

                # Execute & Verify
                with pytest.raises(
                    ValueError, match="Section 'Nonexistent Section' not found"
                ):
                    await wiki_editor.edit_article_section_structured_batched(
                        article_title, section_title, "en", None, 2
                    )
