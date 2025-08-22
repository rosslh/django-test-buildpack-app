"""Test cases for EditOrchestrator service."""

import asyncio
from typing import List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from services.core.interfaces import (
    IContentClassifier,
    IDocumentProcessor,
    IReferenceHandler,
    IReversionTracker,
    ParagraphProcessingResult,
)
from services.editing.edit_orchestrator import (
    EditOrchestrator,
    EditResult,
    EditTask,
    ParagraphResult,
    SkippedItem,
)


# Test helper classes
class SimpleDocumentProcessor(IDocumentProcessor):
    def process(self, text):
        return []


class SimpleContentClassifier(IContentClassifier):
    """Simple test content classifier."""

    def __init__(self):
        self._first_prose_encountered = False
        self._in_footer_section = False

    def should_process_with_context(
        self, content: str, index: int, document_items: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Test implementation that considers context."""
        # Simple logic for testing
        should_process = content.startswith("This is a test paragraph")
        skip_reason = None if should_process else "Test skip reason"
        return should_process, skip_reason

    def reset_state(self) -> None:
        """Reset internal state for testing."""
        self._first_prose_encountered = False
        self._in_footer_section = False

    def get_content_type(self, content: str) -> str:
        """Simple content type classification for testing."""
        if content.startswith("This is a test paragraph"):
            return "prose"
        return "non-prose"

    def is_in_footer_section(self) -> bool:
        """Check if the classifier is currently in a footer section."""
        return self._in_footer_section

    def has_first_prose_been_encountered(self) -> bool:
        """Check if the first prose paragraph has been encountered."""
        return self._first_prose_encountered

    def is_in_lead_section(self) -> bool:
        """Check if the classifier is currently in the lead section."""
        return True  # For testing, assume we're always in lead section


class SimpleReversionTracker(IReversionTracker):
    def reset(self):
        pass

    def get_summary(self):
        return None

    def record_reversion(self, reversion_type):
        pass


class TestEditOrchestrator:
    """Test cases for EditOrchestrator."""

    def setup_method(self, method):
        """Set up test fixtures."""
        # Use minimal real implementations where possible to avoid mocking issues
        self._setup_test_components()
        self._setup_mock_components()
        self._setup_orchestrator()
        self._setup_mock_handlers()

    def _setup_test_components(self):
        """Set up simple test component implementations."""
        self.document_processor = SimpleDocumentProcessor()
        self.content_classifier = SimpleContentClassifier()
        self.reversion_tracker = SimpleReversionTracker()

    def _setup_mock_components(self):
        """Set up mock components for testing."""
        self.mock_reversion_tracker = Mock(spec=IReversionTracker)
        self.mock_reference_handler = Mock(spec=IReferenceHandler)

    def _setup_orchestrator(self):
        """Set up the orchestrator instance."""
        self.orchestrator = EditOrchestrator(
            document_processor=self.document_processor,
            content_classifier=self.content_classifier,
            reversion_tracker=self.mock_reversion_tracker,
            reference_handler=self.mock_reference_handler,
        )

    def _setup_mock_handlers(self):
        """Set up mock handlers and processors."""
        self.mock_reference_handler.replace_references_with_placeholders.return_value = (
            "content",
            [],
        )
        # Mock paragraph processor for orchestrate_edit
        self.mock_paragraph_processor = AsyncMock()
        # Configure process method to avoid coroutine warnings
        self.mock_paragraph_processor.process = AsyncMock()

    def teardown_method(self):
        """Clean up any remaining resources."""
        # Ensure no coroutines are left hanging
        pass

    def test_init_with_default_params(self):
        """Test initialization with default parameters."""
        orchestrator = EditOrchestrator(
            document_processor=self.document_processor,
            content_classifier=self.content_classifier,
            reversion_tracker=self.reversion_tracker,
            reference_handler=self.mock_reference_handler,
        )
        assert orchestrator.document_processor is not None
        assert orchestrator.content_classifier is not None
        assert orchestrator.reversion_tracker is not None
        assert orchestrator.reference_handler is not None

    @pytest.mark.asyncio
    async def test_orchestrate_edit_no_prose_items(self, monkeypatch):
        """Test orchestrating an edit with no prose items."""
        mock_processor = MagicMock(spec=IDocumentProcessor)
        mock_processor.process.return_value = ["non-prose"]
        monkeypatch.setattr(self.orchestrator, "document_processor", mock_processor)

        result = await self.orchestrator.orchestrate_edit_structured(
            "no prose", MagicMock()
        )
        assert len(result) == 1
        assert result[0].status == "SKIPPED"
        assert result[0].before == "non-prose"
        assert result[0].after == "non-prose"
        self.mock_reversion_tracker.reset.assert_called_once()
        mock_processor.process.assert_called_once_with("no prose")

    @pytest.mark.asyncio
    async def test_orchestrate_edit_with_prose_items(self, monkeypatch):
        """Test orchestration with prose items."""
        mock_processor = MagicMock(spec=IDocumentProcessor)
        mock_processor.process.return_value = [
            "prose one",
            "prose two",
            "non-prose",
        ]
        monkeypatch.setattr(self.orchestrator, "document_processor", mock_processor)

        mock_classifier = MagicMock(spec=IContentClassifier)

        def mock_should_process_with_context(content, index, document_items):
            # Skip first prose paragraph, process second prose paragraph, skip non-prose
            if content == "prose one":
                return False, "Skip first prose"  # Skip first prose
            elif content == "prose two":
                return True, None  # Process second prose
            else:
                return False, "Skip non-prose"  # Skip non-prose

        mock_classifier.should_process_with_context.side_effect = (
            mock_should_process_with_context
        )
        mock_classifier.reset_state.return_value = None
        monkeypatch.setattr(self.orchestrator, "content_classifier", mock_classifier)

        mock_paragraph_processor = MagicMock()
        mock_paragraph_processor.process = AsyncMock(
            return_value=ParagraphProcessingResult(success=True, content="edited prose")
        )
        self.mock_reversion_tracker.get_summary.return_value = "summary"

        result = await self.orchestrator.orchestrate_edit_structured(
            "prose one\nprose two\nnon-prose", mock_paragraph_processor
        )

        assert len(result) == 3
        assert result[0].status == "SKIPPED"
        assert result[1].status == "CHANGED"
        assert result[1].before == "prose two"
        assert result[1].after == "edited prose"
        assert result[2].status == "SKIPPED"
        self.mock_reversion_tracker.reset.assert_called_once()
        mock_processor.process.assert_called_once_with(
            "prose one\nprose two\nnon-prose"
        )
        self.mock_reversion_tracker.get_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_edit_tasks_parallel_success(self):
        """Test successful parallel processing of edit tasks."""
        # Setup
        tasks = [
            EditTask("content1", 0, 0, True, 1),
            EditTask("content2", 1, 1, False, 2),
        ]
        paragraph_processor = AsyncMock()

        # Use async return values properly
        async def mock_process_side_effect(content, context):
            if content == "content1":
                return ParagraphProcessingResult(success=True, content="edited1")
            elif content == "content2":
                return ParagraphProcessingResult(success=True, content="edited2")
            return ParagraphProcessingResult(success=True, content=content)

        paragraph_processor.process.side_effect = mock_process_side_effect

        with patch(
            "services.text.reference_handler.ReferenceHandler.replace_references_with_placeholders"
        ) as mock_replace:
            mock_replace.return_value = ("text", [])

            # Execute
            assert self.orchestrator is not None
            results = await self.orchestrator._process_edit_tasks(
                tasks, paragraph_processor
            )

        # Verify
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].content == "edited1"
        assert results[1].content == "edited2"

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_process_edit_tasks_runtime_error_reraise(self, monkeypatch):
        """Test that non-event-loop RuntimeErrors are re-raised."""
        # Setup
        tasks = [EditTask("content1", 0, 0, True, 1)]
        # Use a regular Mock since the paragraph_processor won't be called due to RuntimeError
        paragraph_processor = Mock()

        # Mock asyncio.gather to raise RuntimeError immediately, preventing any coroutine creation
        with patch("asyncio.gather", side_effect=RuntimeError("another error")):
            # Execute & Verify
            assert self.orchestrator is not None
            with pytest.raises(RuntimeError, match="another error"):
                await self.orchestrator._process_edit_tasks(tasks, paragraph_processor)

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_process_edit_tasks(self):
        """Test concurrent processing of edit tasks."""
        # Setup
        tasks = [
            EditTask("content1", 0, 0, True, 1),
            EditTask("content2", 1, 1, False, 2),
        ]
        paragraph_processor = AsyncMock()

        async def mock_process_side_effect(content, context):
            if content == "content1":
                return ParagraphProcessingResult(success=True, content="edited1")
            elif content == "content2":
                return ParagraphProcessingResult(success=True, content="edited2")
            return ParagraphProcessingResult(success=True, content=content)

        paragraph_processor.process.side_effect = mock_process_side_effect

        with patch(
            "services.text.reference_handler.ReferenceHandler.replace_references_with_placeholders"
        ) as mock_replace:
            mock_replace.return_value = ("text", [])

            # Execute
            assert self.orchestrator is not None
            results = await self.orchestrator._process_edit_tasks(
                tasks, paragraph_processor
            )

        # Verify
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].content == "edited1"
        assert results[1].content == "edited2"

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_process_single_task_success(self):
        """Test successful processing of a single task."""
        # Setup
        task = EditTask("content", 0, 0, True, 1)
        paragraph_processor = AsyncMock()

        async def mock_process(content, context):
            return ParagraphProcessingResult(success=True, content="edited")

        paragraph_processor.process.side_effect = mock_process

        with patch(
            "services.text.reference_handler.ReferenceHandler.replace_references_with_placeholders"
        ) as mock_replace:
            mock_replace.return_value = ("text", [])

            # Execute
            assert self.orchestrator is not None
            result = await self.orchestrator._process_single_task(
                task, paragraph_processor
            )

        # Verify
        assert result.success
        assert result.content == "edited"
        # Note: progress observer calls are not verified as we use real objects

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_process_single_task_exception_handling(self):
        """Test exception handling in single task processing."""
        # Setup
        task = EditTask("content", 0, 0, True, 1)
        paragraph_processor = AsyncMock()
        test_exception = Exception("Processing failed")

        # Configure the AsyncMock to raise an exception without creating a coroutine
        async def raise_exception(*args, **kwargs):
            raise test_exception

        paragraph_processor.process.side_effect = raise_exception

        with patch(
            "services.text.reference_handler.ReferenceHandler.replace_references_with_placeholders"
        ) as mock_replace:
            mock_replace.return_value = ("text", [])

            # Execute
            assert self.orchestrator is not None
            result = await self.orchestrator._process_single_task(
                task, paragraph_processor
            )

        # Verify
        assert not result.success
        assert result.content == "content"  # Original content returned
        assert isinstance(result.error, Exception)
        assert str(result.error) == "Processing failed"

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_create_edit_tasks(self):
        """Test the creation of edit tasks from document items."""
        # Add a dummy first paragraph to be skipped
        document_items = ["dummy first paragraph", "prose", "== Section =="]
        assert self.orchestrator is not None
        with (
            patch.object(
                self.orchestrator.content_classifier,
                "should_process_with_context",
                side_effect=[
                    (
                        False,
                        "First prose paragraph in lead section - skipped to preserve article structure",
                    ),  # Skip first prose
                    (True, None),  # Process second
                    (False, "Section heading"),  # Skip section
                ],
            ),
            patch.object(
                self.orchestrator.content_classifier,
                "get_content_type",
                side_effect=["prose", "prose", "heading"],
            ),
        ):
            # Execute
            tasks, skipped_items = (
                self.orchestrator._create_edit_tasks_and_skipped_items(document_items)
            )

        # Verify tasks
        assert len(tasks) == 1
        assert isinstance(tasks[0], EditTask)
        assert tasks[0].content == "prose"
        assert tasks[0].is_first_prose is False
        assert tasks[0].prose_index == 0
        assert tasks[0].document_index == 1

        # Verify skipped items
        assert len(skipped_items) == 2
        assert skipped_items[0].document_index == 0
        assert skipped_items[0].content == "dummy first paragraph"
        assert skipped_items[0].content_type == "prose"
        assert (
            skipped_items[0].skip_reason
            == "First prose paragraph in lead section - skipped to preserve article structure"
        )
        assert skipped_items[1].document_index == 2
        assert skipped_items[1].content == "== Section =="
        assert skipped_items[1].content_type == "heading"
        assert skipped_items[1].skip_reason == "Section heading"

    def test_create_validation_context(self):
        """Test creating a validation context."""
        task = EditTask(
            content="original content with <ref>test</ref>",
            document_index=1,
            prose_index=0,
            is_first_prose=True,
            total_prose=1,
        )
        self.mock_reference_handler.replace_references_with_placeholders.return_value = (
            "placeholders",
            ["<ref>test</ref>"],
        )
        context = self.orchestrator._create_validation_context(task)
        assert context.paragraph_index == 0
        assert context.total_paragraphs == 1
        assert context.is_first_prose
        assert context.refs_list == ["<ref>test</ref>"]
        assert (
            context.additional_data["original_content"]
            == "original content with <ref>test</ref>"
        )
        assert context.additional_data["text_with_placeholders"] == "placeholders"

    def test_assemble_document(self):
        """Test document assembly from results."""
        # Setup
        original_items = ["# Header", "old content 1", "== Section ==", "old content 2"]
        tasks = [
            EditTask("old content 1", 1, 0, True, 2),
            EditTask("old content 2", 3, 1, False, 2),
        ]
        results = [
            EditResult(success=True, content="new content 1"),
            EditResult(
                success=False, content="old content 2", error=Exception("Failed")
            ),
        ]

        # Execute
        assert self.orchestrator is not None
        final_text = self.orchestrator._assemble_document(
            original_items, tasks, results
        )

        # Verify
        expected = "# Header\nnew content 1\n== Section ==\nold content 2"
        assert final_text == expected

    def test_parse_document_structure_exception(self):
        """Test _parse_document_structure handles exceptions properly."""
        mock_processor = MagicMock(spec=IDocumentProcessor)
        mock_processor.process.side_effect = Exception("Document parsing error")

        orchestrator = EditOrchestrator(
            document_processor=mock_processor,
            content_classifier=self.content_classifier,
            reversion_tracker=self.reversion_tracker,
            reference_handler=self.mock_reference_handler,
        )

        with pytest.raises(Exception, match="Document parsing error"):
            orchestrator._parse_document_structure("test text")

    def test_analyze_and_create_edit_tasks_exception(self, monkeypatch):
        """Test _analyze_and_create_edit_tasks handles exceptions properly."""

        # Mock _create_edit_tasks_and_skipped_items to raise an exception
        def mock_create_edit_tasks_and_skipped_items(document_items):
            raise Exception("Edit task creation error")

        monkeypatch.setattr(
            self.orchestrator,
            "_create_edit_tasks_and_skipped_items",
            mock_create_edit_tasks_and_skipped_items,
        )

        with pytest.raises(Exception, match="Edit task creation error"):
            self.orchestrator._analyze_and_create_edit_tasks(["test item"])

    @pytest.mark.asyncio
    async def test_process_and_create_results_exception(self, monkeypatch):
        """Test exception handling in _process_and_create_results returns ERRORED."""
        document_items = ["item1", "item2"]
        edit_tasks = [
            EditTask("item1", 0, 0, True, 1),
            EditTask("item2", 1, 1, False, 2),
        ]
        skipped_items: List[SkippedItem] = []

        async def mock_process_edit_tasks(edit_tasks, paragraph_processor):
            raise Exception("Edit task processing error")

        monkeypatch.setattr(
            self.orchestrator, "_process_edit_tasks", mock_process_edit_tasks
        )

        paragraph_processor = AsyncMock()

        results = await self.orchestrator._process_and_create_results(
            edit_tasks, skipped_items, document_items, paragraph_processor
        )

        # Should return ParagraphResult with ERRORED status for each item
        assert len(results) == len(document_items)
        for i, result in enumerate(results):
            assert isinstance(result, ParagraphResult)
            assert result.before == document_items[i]
            assert result.after == document_items[i]
            assert result.status == "ERRORED"
            assert "Error during task processing" in result.status_details

    @pytest.mark.asyncio
    async def test_process_and_create_results_paragraph_results_exception(
        self, monkeypatch
    ):
        """Test _process_and_create_results handles paragraph results creation exceptions."""

        # Mock _process_edit_tasks to succeed but return invalid results
        async def mock_process_edit_tasks(edit_tasks, paragraph_processor):
            return [EditResult(success=True, content="edited")]

        monkeypatch.setattr(
            self.orchestrator, "_process_edit_tasks", mock_process_edit_tasks
        )

        # Mock ParagraphResult to raise an exception when created
        def mock_paragraph_result(*args, **kwargs):
            raise Exception("ParagraphResult creation error")

        monkeypatch.setattr(
            "services.editing.edit_orchestrator.ParagraphResult",
            mock_paragraph_result,
        )

        edit_tasks = [EditTask("content", 0, 0, False, 1)]
        skipped_items: List[SkippedItem] = []
        document_items = ["content"]
        mock_paragraph_processor = AsyncMock()

        with pytest.raises(Exception, match="ParagraphResult creation error"):
            await self.orchestrator._process_and_create_results(
                edit_tasks, skipped_items, document_items, mock_paragraph_processor
            )

    def test_display_summary_with_summary(self):
        """Test _display_summary when tracker has a summary."""
        self.mock_reversion_tracker.get_summary.return_value = "Test summary"

        # Capture print output
        import io
        import sys

        captured_output = io.StringIO()
        sys.stdout = captured_output

        self.orchestrator._display_summary()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        assert "Test summary" in output

    def test_display_summary_without_summary(self):
        """Test _display_summary when tracker has no summary."""
        self.mock_reversion_tracker.get_summary.return_value = None

        self.orchestrator._display_summary()

    @pytest.mark.asyncio
    async def test_orchestrate_edit_skips_footer_sections(self, monkeypatch):
        """Test that footer sections are skipped."""
        # Add a dummy first paragraph to be skipped
        items = ["dummy first paragraph", "prose", "==See also==", "content"]
        mock_processor = MagicMock()
        mock_processor.process.return_value = items
        monkeypatch.setattr(self.orchestrator, "document_processor", mock_processor)

        mock_classifier = MagicMock()

        def mock_should_process_with_context(content, index, document_items):
            # Skip first prose, process second prose, skip footer heading and footer content
            if content == "dummy first paragraph":
                return False, "Skip first prose"  # Skip first prose
            elif content == "prose":
                return True, None  # Process second prose
            else:
                return (
                    False,
                    "Skip footer heading and footer content",
                )  # Skip footer heading and footer content

        mock_classifier.should_process_with_context.side_effect = (
            mock_should_process_with_context
        )
        mock_classifier.reset_state.return_value = None
        monkeypatch.setattr(self.orchestrator, "content_classifier", mock_classifier)

        mock_paragraph_processor = MagicMock()
        mock_paragraph_processor.process = AsyncMock(
            return_value=ParagraphProcessingResult(success=True, content="edited prose")
        )

        result = await self.orchestrator.orchestrate_edit_structured(
            "dummy first paragraph\nprose\n==See also==\ncontent",
            mock_paragraph_processor,
        )

        assert len(result) == 4
        assert result[0].status == "SKIPPED"
        assert result[1].status == "CHANGED"
        assert result[1].before == "prose"
        assert result[1].after == "edited prose"
        assert result[2].status == "SKIPPED"
        assert result[3].status == "SKIPPED"
        mock_paragraph_processor.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_edit_structured_returns_paragraph_results(
        self, monkeypatch
    ):
        """Test that orchestrate_edit_structured returns structured paragraph results."""
        text = (
            "First paragraph.\n\nSecond paragraph.\n\n== Heading ==\n\nThird paragraph."
        )
        document_items = [
            "First paragraph.",
            "Second paragraph.",
            "== Heading ==",
            "Third paragraph.",
        ]

        # Setup mocks
        self._setup_structured_test_mocks(monkeypatch, document_items)
        mock_processor = self._create_test_paragraph_processor()

        # Execute
        results = await self.orchestrator.orchestrate_edit_structured(
            text, mock_processor
        )

        # Verify results structure
        self._verify_structured_results_format(results)

        # Verify specific result contents
        self._verify_structured_results_content(results)

    def _setup_structured_test_mocks(self, monkeypatch, document_items):
        """Set up mocks for structured test."""
        # Mock document processor
        mock_doc_processor = MagicMock(spec=IDocumentProcessor)
        mock_doc_processor.process.return_value = document_items
        monkeypatch.setattr(self.orchestrator, "document_processor", mock_doc_processor)

        # Mock content classifier
        mock_classifier = MagicMock(spec=IContentClassifier)
        mock_classifier.should_process_with_context.side_effect = (
            self._mock_should_process_with_context
        )
        mock_classifier.get_content_type.side_effect = self._mock_get_content_type
        mock_classifier.reset_state.return_value = None
        monkeypatch.setattr(self.orchestrator, "content_classifier", mock_classifier)

    def _mock_should_process_with_context(self, content, index, document_items):
        """Mock function to determine if content should be processed."""
        # Skip first prose paragraph, skip second prose paragraph (both first two prose),
        # skip heading, process third paragraph (first prose that's not skipped)
        if content == "First paragraph.":
            return False, "Skip first prose"  # Skip first prose
        elif content == "Second paragraph.":
            return (
                False,
                "Skip second prose (still considered first prose in business logic)",
            )  # Skip second prose
        elif content.startswith("=="):
            return False, "Skip headings"  # Skip headings
        elif content == "Third paragraph.":
            return (
                True,
                None,
            )  # Process third paragraph (first prose that's not skipped)
        return False, "Skip by default"

    def _mock_get_content_type(self, content):
        """Mock function to get content type."""
        if content.startswith("=="):
            return "heading"
        return "prose"

    def _create_test_paragraph_processor(self):
        """Create a paragraph processor for structured result tests."""
        paragraph_processor = AsyncMock()

        async def mock_process(content, context):
            if "first" in content.lower():
                return ParagraphProcessingResult(
                    success=True, content="Modified first paragraph."
                )
            elif "second" in content.lower():
                # Simulate a rejected edit
                return ParagraphProcessingResult(
                    success=False,
                    content=content,
                    failure_reason="Simulated rejection",
                )
            elif "third" in content.lower():
                return ParagraphProcessingResult(
                    success=True, content="Modified third paragraph."
                )
            return ParagraphProcessingResult(success=True, content=content)

        paragraph_processor.process.side_effect = mock_process
        return paragraph_processor

    def _verify_structured_results_format(self, results):
        """Verify the format of structured results."""
        assert isinstance(results, list)
        assert len(results) == 4  # Should have 4 paragraphs

        # All results should be ParagraphResult objects
        for result in results:
            assert isinstance(result, ParagraphResult)
            assert hasattr(result, "before")
            assert hasattr(result, "after")
            assert hasattr(result, "status")
            assert hasattr(result, "status_details")
            assert result.status in [
                "CHANGED",
                "UNCHANGED",
                "REJECTED",
                "SKIPPED",
                "ERRORED",
            ]

    def _verify_structured_results_content(self, results):
        """Verify the content of structured results."""
        # First paragraph should be skipped (first prose paragraph)
        assert results[0].before == "First paragraph."
        assert results[0].after == "First paragraph."
        assert results[0].status == "SKIPPED"

        # Second paragraph should be skipped (also considered first prose due to business logic)
        assert results[1].before == "Second paragraph."
        assert results[1].after == "Second paragraph."
        assert results[1].status == "SKIPPED"

        # Heading should be skipped (non-prose)
        assert results[2].before == "== Heading =="
        assert results[2].after == "== Heading =="
        assert results[2].status == "SKIPPED"

        # Third paragraph should be changed (first prose paragraph that's not skipped)
        assert results[3].before == "Third paragraph."
        assert results[3].after == "Modified third paragraph."
        assert results[3].status == "CHANGED"

    @pytest.mark.asyncio
    async def test_orchestrate_edit_structured_no_edit_tasks(self, monkeypatch):
        """Test orchestrate_edit_structured when there are no edit tasks."""
        # Setup document processor to return items but content classifier to reject all
        mock_processor = MagicMock(spec=IDocumentProcessor)
        mock_processor.process.return_value = [
            "== Heading ==",
            "Some non-prose content",
            "{{template}}",
        ]
        monkeypatch.setattr(self.orchestrator, "document_processor", mock_processor)

        # Content classifier that rejects all content (no prose items)
        mock_classifier = MagicMock(spec=IContentClassifier)
        mock_classifier.should_process_with_context.return_value = (
            False,
            "Non-prose content",
        )
        mock_classifier.get_content_type.return_value = "non-prose"
        mock_classifier.reset_state.return_value = None
        monkeypatch.setattr(self.orchestrator, "content_classifier", mock_classifier)

        # Execute
        result = await self.orchestrator.orchestrate_edit_structured(
            "== Heading ==\nSome non-prose content\n{{template}}",
            self.mock_paragraph_processor,
        )

        # Verify - should return all items as SKIPPED since no edit tasks were created (all non-prose)
        assert len(result) == 3
        assert all(paragraph_result.status == "SKIPPED" for paragraph_result in result)
        assert result[0].before == "== Heading =="
        assert result[0].after == "== Heading =="
        assert result[1].before == "Some non-prose content"
        assert result[1].after == "Some non-prose content"
        assert result[2].before == "{{template}}"
        assert result[2].after == "{{template}}"

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_orchestrate_edit_structured_with_failed_edit_task(self, monkeypatch):
        """Test orchestrating a structured edit where one task fails."""
        text = "prose1\n\nprose2\n\nprose3"
        document_items = ["prose1", "prose2", "prose3"]
        monkeypatch.setattr(
            self.orchestrator.document_processor, "process", lambda _: document_items
        )
        monkeypatch.setattr(
            self.orchestrator.content_classifier,
            "should_process_with_context",
            lambda content, index, document_items: (True, "prose"),
        )

        async def mock_process_side_effect(content, context):
            if content == "prose2":
                raise ValueError("Task failed")
            return ParagraphProcessingResult(success=True, content=f"edited {content}")

        self.mock_paragraph_processor.process.side_effect = mock_process_side_effect

        # Act
        result = await self.orchestrator.orchestrate_edit_structured(
            text, self.mock_paragraph_processor
        )

        # Assert
        assert len(result) == 3
        assert result[0].status == "CHANGED"
        assert result[1].status == "ERRORED"
        assert "ValueError" in result[1].status_details
        assert result[2].status == "CHANGED"

    @pytest.mark.asyncio
    async def test_orchestrate_edit_structured_partial_failure(self, monkeypatch):
        """Test a partial failure where one processor fails and another succeeds."""
        text = "non-prose\n\nprose1\n\nprose2\n\nprose3"
        document_items = ["non-prose", "prose1", "prose2", "prose3"]
        monkeypatch.setattr(
            self.orchestrator.document_processor, "process", lambda _: document_items
        )

        side_effects = [
            (False, "non-prose"),
            (True, "prose"),
            (True, "prose"),
            (True, "prose"),
        ]
        mock_should_process = MagicMock(side_effect=side_effects)
        monkeypatch.setattr(
            self.orchestrator.content_classifier,
            "should_process_with_context",
            mock_should_process,
        )

        # Mock paragraph processor to fail for the second prose item
        async def mock_process(content, context):
            if content == "prose1":
                return ParagraphProcessingResult(success=True, content="edited prose1")
            if content == "prose2":
                raise ValueError("Processing failed")
            if content == "prose3":
                return ParagraphProcessingResult(success=True, content="edited prose3")
            return ParagraphProcessingResult(success=True, content=content)

        self.mock_paragraph_processor.process.side_effect = mock_process

        results = await self.orchestrator.orchestrate_edit_structured(
            text, self.mock_paragraph_processor
        )

        assert len(results) == 4
        assert results[0].status == "SKIPPED"
        assert results[1].status == "CHANGED"
        assert results[2].status == "ERRORED"
        assert "ValueError" in results[2].status_details
        assert results[3].status == "CHANGED"

    def test_create_result_for_processed_item_unchanged(self):
        """Test _create_result_for_processed_item when content is unchanged."""
        item = "Test content"
        edit_result = EditResult(
            success=True, content="Test content"
        )  # Same as original

        result = self.orchestrator._create_result_for_processed_item(item, edit_result)

        assert result.status == "UNCHANGED"
        assert result.status_details == "Content was processed but no changes were made"
        assert result.before == item
        assert result.after == "Test content"

    def test_create_result_for_processed_item_rejected_with_failure_reason(self):
        """Test _create_result_for_processed_item when edit is rejected with failure reason."""
        item = "Test content"
        edit_result = EditResult(
            success=False, content="Test content", failure_reason="Validation failed"
        )

        result = self.orchestrator._create_result_for_processed_item(item, edit_result)

        assert result.status == "REJECTED"
        assert result.status_details == "Edit failed validation: Validation failed"
        assert result.before == item
        assert result.after == item

    def test_create_result_for_processed_item_rejected_without_failure_reason(self):
        """Test _create_result_for_processed_item when edit is rejected without failure reason."""
        item = "Test content"
        edit_result = EditResult(
            success=False, content="Test content"
        )  # No failure_reason

        result = self.orchestrator._create_result_for_processed_item(item, edit_result)

        assert result.status == "REJECTED"
        assert (
            result.status_details
            == "Edit was made but failed validation and was reverted"
        )
        assert result.before == item
        assert result.after == item

    def test_create_result_for_skipped_item(self):
        """Test _create_result_for_skipped_item for different skip scenarios."""
        from services.editing.edit_orchestrator import SkippedItem

        # Test footer section prose
        skipped_item = SkippedItem(
            content="This is prose content in a footer section.",
            document_index=2,
            content_type="prose",
            skip_reason="Prose content in footer section - skipped per editorial guidelines",
        )

        result = self.orchestrator._create_result_for_skipped_item(skipped_item)

        assert isinstance(result, ParagraphResult)
        assert result.before == skipped_item.content
        assert result.after == skipped_item.content
        assert result.status == "SKIPPED"
        assert (
            result.status_details
            == "Prose content in footer section - skipped per editorial guidelines"
        )

    @pytest.mark.asyncio
    async def test_orchestrate_edit_structured_provides_real_time_progress(
        self, monkeypatch
    ):
        """Test that progress callback is called in real-time as individual tasks complete."""
        text = "prose1\n\nprose2\n\nprose3"
        document_items = ["prose1", "prose2", "prose3"]

        # Setup document processor and classifier
        monkeypatch.setattr(
            self.orchestrator.document_processor, "process", lambda _: document_items
        )
        monkeypatch.setattr(
            self.orchestrator.content_classifier,
            "should_process_with_context",
            lambda content, index, document_items: (True, "prose"),
        )

        # Track progress callback invocations with timestamps
        progress_calls = []
        import time

        start_time = time.time()

        def track_progress(progress_data):
            """Track progress callback calls with timing."""
            progress_calls.append(
                {
                    "progress_percentage": progress_data["progress_percentage"],
                    "total_paragraphs": progress_data["total_paragraphs"],
                    "phase_counts": progress_data["phase_counts"],
                    "completed_count": progress_data["phase_counts"]["complete"],
                    "timestamp": time.time() - start_time,
                }
            )

        # Setup paragraph processor with staggered delays to test real-time behavior
        task_completion_order = []

        async def staggered_process(content, context):
            """Simulate processing with different delays per task."""
            if content == "prose1":
                await asyncio.sleep(0.1)  # 100ms
            elif content == "prose2":
                await asyncio.sleep(0.05)  # 50ms (completes first)
            elif content == "prose3":
                await asyncio.sleep(0.15)  # 150ms (completes last)

            task_completion_order.append(content)
            return ParagraphProcessingResult(success=True, content=f"edited {content}")

        self.mock_paragraph_processor.process.side_effect = staggered_process

        # Execute with progress tracking
        await self.orchestrator.orchestrate_edit_structured(
            text,
            self.mock_paragraph_processor,
            enhanced_progress_callback=track_progress,
        )

        # The key test: progress should be reported as tasks complete individually,
        # not all at once after everything is done. With the current buggy implementation,
        # all progress calls happen at the same time after gather() completes.

        # Verify progress was reported multiple times (initial + phase transitions for each paragraph)
        # Each paragraph goes through: pending -> pre_processing -> llm_processing -> post_processing -> complete
        # Plus the initial call, we should have multiple progress updates
        assert len(progress_calls) >= 3, (
            f"Expected at least 3 progress calls, got {len(progress_calls)}"
        )

        # CRITICAL TEST: If this is real-time progress, the timestamps should be spread out
        # based on when each task actually completes, not bunched together at the end.
        # With current implementation, all timestamps will be nearly identical because
        # they all happen after asyncio.gather() returns.

        time_differences = []
        for i in range(1, len(progress_calls)):
            time_diff = (
                progress_calls[i]["timestamp"] - progress_calls[i - 1]["timestamp"]
            )
            time_differences.append(time_diff)

        # In real-time progress, we should see meaningful time gaps between progress calls
        # since tasks complete at different times. Current implementation fails this test
        # because all progress callbacks happen in rapid succession after gather() completes.
        min_expected_gap = 0.01  # 10ms minimum gap expected between real-time updates

        # This assertion should FAIL with current implementation
        gaps_too_small = [diff < min_expected_gap for diff in time_differences]
        assert not all(gaps_too_small), (
            f"Progress callbacks happened too close together (gaps: {time_differences}), "
            f"indicating they're not happening in real-time as tasks complete. "
            f"Current implementation waits for all tasks to finish before reporting any progress."
        )

    @pytest.mark.asyncio
    async def test_process_and_create_results_item_not_in_either_map(self, monkeypatch):
        """Test the fallback case where an item is neither processed nor skipped."""
        # Create a scenario where we have an item that doesn't appear in either map
        document_items = ["item1", "item2"]
        edit_tasks: List[EditTask] = []  # No edit tasks
        skipped_items: List[SkippedItem] = []  # No skipped items

        # Mock to return empty edit results
        async def mock_process_edit_tasks(edit_tasks, paragraph_processor):
            return []

        monkeypatch.setattr(
            self.orchestrator, "_process_edit_tasks", mock_process_edit_tasks
        )

        paragraph_processor = AsyncMock()

        results = await self.orchestrator._process_and_create_results(
            edit_tasks, skipped_items, document_items, paragraph_processor
        )

        # Should return ParagraphResult with "unknown reason" for each item
        assert len(results) == 2
        for result in results:
            assert result.status == "SKIPPED"
            assert result.status_details == "Item not processed for unknown reason"

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_process_edit_tasks_runtime_error_not_event_loop(self, monkeypatch):
        """Test that a non-event-loop RuntimeError is reraised."""
        tasks = [EditTask("content", 0, 0, False, 1)]
        paragraph_processor = AsyncMock()

        # Patch _process_single_task with an AsyncMock
        from unittest.mock import AsyncMock as PatchAsyncMock

        mock_process_single_task = PatchAsyncMock(
            side_effect=self.orchestrator._process_single_task
        )
        monkeypatch.setattr(
            self.orchestrator, "_process_single_task", mock_process_single_task
        )

        # Mock asyncio.gather to raise RuntimeError with different message
        async def mock_gather(*args, **kwargs):
            raise RuntimeError("different error")

        monkeypatch.setattr(asyncio, "gather", mock_gather)

        # This should re-raise the RuntimeError instead of falling back
        with pytest.raises(RuntimeError, match="different error"):
            await self.orchestrator._process_edit_tasks(tasks, paragraph_processor)

    @pytest.mark.asyncio
    async def test_process_single_task_with_failure_reason(self):
        """Test _process_single_task when processor has failure_reason."""
        # Create a task
        task = EditTask(
            content="test content",
            document_index=0,
            prose_index=0,
            is_first_prose=True,
            total_prose=1,
        )

        # Create a mock processor that has a failure_reason
        mock_processor = AsyncMock()
        mock_processor.process.return_value = ParagraphProcessingResult(
            success=False,
            content="test content",
            failure_reason="Validation failed: too many changes",
        )

        result = await self.orchestrator._process_single_task(task, mock_processor)

        assert result.success is False
        assert result.content == "test content"
        assert result.failure_reason == "Validation failed: too many changes"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_process_single_task_with_exception_logging(self):
        """Test _process_single_task when exception occurs and gets logged."""
        task = EditTask(
            content="Test content",
            document_index=0,
            prose_index=0,
            is_first_prose=False,
            total_prose=1,
        )

        # Mock paragraph processor to raise exception
        mock_paragraph_processor = AsyncMock()
        mock_paragraph_processor.process.side_effect = Exception("Processing error")

        # Create validation context
        self.mock_reference_handler.replace_references_with_placeholders.return_value = (
            "Test content",
            [],
        )

        # Call the async method properly to avoid coroutine warning
        result = await self.orchestrator._process_single_task(
            task, mock_paragraph_processor
        )

        assert result.success is False
        assert result.content == "Test content"
        assert isinstance(result.error, Exception)
        assert str(result.error) == "Processing error"

    @pytest.mark.asyncio
    async def test_process_edit_tasks_with_base_exception_in_gather(self):
        """Test _process_edit_tasks handles BaseException from asyncio.gather."""
        tasks = [EditTask("content1", 0, 0, True, 1)]
        paragraph_processor = AsyncMock()

        # Mock asyncio.gather to return BaseException in results (properly awaitable)
        async def mock_gather(*coroutines, **kwargs):
            # Properly close any coroutines to avoid warnings
            for coro in coroutines:
                if hasattr(coro, "close"):
                    coro.close()
            return [ValueError("test error")]

        with patch("asyncio.gather", side_effect=mock_gather):
            assert self.orchestrator is not None
            results = await self.orchestrator._process_edit_tasks(
                tasks, paragraph_processor
            )

            # Should have one result with error
            assert len(results) == 1
            assert results[0].success is False
            assert isinstance(results[0].error, ValueError)

    @pytest.mark.asyncio
    async def test_process_single_task_with_base_exception(self):
        """Test _process_single_task handles BaseException from gather."""
        tasks = [EditTask("content1", 0, 0, True, 1)]

        # Create a mock paragraph processor that will cause BaseException in gather
        async def failing_process(content, context):
            raise ValueError("test processing error")

        paragraph_processor = AsyncMock()
        paragraph_processor.process.side_effect = failing_process

        async def mock_gather(*coroutines, **kwargs):
            # Properly close any coroutines to avoid warnings
            for coro in coroutines:
                if hasattr(coro, "close"):
                    coro.close()
            return [ValueError("gather error")]

        with patch("asyncio.gather", side_effect=mock_gather):
            assert self.orchestrator is not None
            results = await self.orchestrator._process_single_task(
                tasks[0], paragraph_processor
            )

            # Should return EditResult with error
            assert results.success is False
            assert isinstance(results.error, ValueError)

    @pytest.mark.asyncio
    async def test_process_and_create_results_handles_base_exception_result(
        self, monkeypatch
    ):
        """Test _process_and_create_results handles BaseException returned from _process_edit_tasks."""
        # Setup
        document_items = ["prose content"]
        edit_tasks = [EditTask("prose content", 0, 0, True, 1)]
        skipped_items: List[SkippedItem] = []

        # Mock _process_edit_tasks to return a BaseException instead of EditResult
        async def mock_process_edit_tasks(tasks, processor):
            return [ValueError("Task processing failed")]

        monkeypatch.setattr(
            self.orchestrator, "_process_edit_tasks", mock_process_edit_tasks
        )

        paragraph_processor = AsyncMock()

        # Execute
        results = await self.orchestrator._process_and_create_results(
            edit_tasks, skipped_items, document_items, paragraph_processor
        )

        # Verify - the BaseException should be converted to an EditResult with error
        assert len(results) == 1
        assert results[0].status == "ERRORED"
        assert "ValueError" in results[0].status_details
        assert "Error during task processing" in results[0].status_details

    @pytest.mark.asyncio
    async def test_orchestrate_edit_structured_batched_success(self):
        """Test successful batched structured edit orchestration."""
        # Setup
        text = "Test paragraph 1\nTest paragraph 2"
        paragraph_processor = AsyncMock()
        enhanced_progress_callback = Mock()
        batch_size = 2

        # Mock document parsing
        document_items = ["Test paragraph 1", "Test paragraph 2"]

        # Mock task creation
        tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 2),
            EditTask("Test paragraph 2", 1, 1, False, 2),
        ]

        # Mock paragraph processing
        paragraph_processor.process.side_effect = [
            ParagraphProcessingResult(success=True, content="Edited paragraph 1"),
            ParagraphProcessingResult(success=True, content="Edited paragraph 2"),
        ]

        with patch.object(
            self.orchestrator.document_processor, "process", lambda _: document_items
        ):
            with patch.object(
                self.orchestrator, "_analyze_and_create_edit_tasks"
            ) as mock_analyze:
                mock_analyze.return_value = (tasks, [])
                with patch.object(
                    self.orchestrator, "_display_summary"
                ):
                    # Execute
                    results = await self.orchestrator.orchestrate_edit_structured_batched(
                        text, paragraph_processor, enhanced_progress_callback, batch_size
                    )

        # Verify
        assert len(results) == 2
        assert enhanced_progress_callback.called

    @pytest.mark.asyncio
    async def test_orchestrate_edit_structured_batched_empty_text(self):
        """Test batched orchestration with empty text."""
        paragraph_processor = AsyncMock()

        # Execute
        results = await self.orchestrator.orchestrate_edit_structured_batched(
            "", paragraph_processor, None, 2
        )

        # Verify
        assert results == []

    @pytest.mark.asyncio
    async def test_process_and_create_results_batched(self):
        """Test batched processing and result creation."""
        # Setup
        document_items = ["Test paragraph 1", "Test paragraph 2"]
        edit_tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 2),
            EditTask("Test paragraph 2", 1, 1, False, 2),
        ]
        skipped_items: List[SkippedItem] = []
        paragraph_processor = AsyncMock()
        batch_size = 2

        # Mock paragraph processing
        paragraph_processor.process.side_effect = [
            ParagraphProcessingResult(success=True, content="Edited paragraph 1"),
            ParagraphProcessingResult(success=True, content="Edited paragraph 2"),
        ]

        with patch.object(
            self.orchestrator, "_create_paragraph_results"
        ) as mock_create_results:
            mock_create_results.return_value = [
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

            # Execute
            results = await self.orchestrator._process_and_create_results_batched(
                edit_tasks, skipped_items, document_items, paragraph_processor, batch_size
            )

        # Verify
        assert len(results) == 2
        assert mock_create_results.called

    @pytest.mark.asyncio
    async def test_execute_edit_tasks_batched_success(self):
        """Test successful batched edit task execution."""
        # Setup
        edit_tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 2),
            EditTask("Test paragraph 2", 1, 1, False, 2),
        ]
        paragraph_processor = AsyncMock()
        batch_size = 2

        # Mock paragraph processing
        paragraph_processor.process.side_effect = [
            ParagraphProcessingResult(success=True, content="Edited paragraph 1"),
            ParagraphProcessingResult(success=True, content="Edited paragraph 2"),
        ]

        with patch.object(
            self.orchestrator, "_process_edit_tasks_batch"
        ) as mock_process_batch:
            mock_process_batch.return_value = [
                EditResult(success=True, content="Edited paragraph 1"),
                EditResult(success=True, content="Edited paragraph 2"),
            ]

            # Execute
            result_map = await self.orchestrator._execute_edit_tasks_batched(
                edit_tasks, paragraph_processor, batch_size
            )

        # Verify
        assert len(result_map) == 2
        assert 0 in result_map
        assert 1 in result_map
        assert result_map[0].success
        assert result_map[1].success

    @pytest.mark.asyncio
    async def test_execute_edit_tasks_batched_empty_tasks(self):
        """Test batched execution with empty task list."""
        paragraph_processor = AsyncMock()

        # Execute
        result_map = await self.orchestrator._execute_edit_tasks_batched(
            [], paragraph_processor, 2
        )

        # Verify
        assert result_map == {}

    @pytest.mark.asyncio
    async def test_execute_edit_tasks_batched_batch_failure(self):
        """Test batched execution when a batch fails."""
        # Setup
        edit_tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 2),
            EditTask("Test paragraph 2", 1, 1, False, 2),
        ]
        paragraph_processor = AsyncMock()
        batch_size = 2

        with patch.object(
            self.orchestrator, "_process_edit_tasks_batch"
        ) as mock_process_batch:
            mock_process_batch.side_effect = RuntimeError("Batch processing failed")

            # Execute
            result_map = await self.orchestrator._execute_edit_tasks_batched(
                edit_tasks, paragraph_processor, batch_size
            )

        # Verify - all tasks should be marked as failed
        assert len(result_map) == 2
        assert not result_map[0].success
        assert not result_map[1].success
        assert isinstance(result_map[0].error, RuntimeError)
        assert isinstance(result_map[1].error, RuntimeError)

    @pytest.mark.asyncio
    async def test_execute_edit_tasks_batched_exception_handling(self):
        """Test batched execution exception handling."""
        # Setup
        edit_tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 1),
        ]
        paragraph_processor = AsyncMock()
        batch_size = 1

        with patch("asyncio.gather", side_effect=Exception("Gather failed")):
            # Execute
            result_map = await self.orchestrator._execute_edit_tasks_batched(
                edit_tasks, paragraph_processor, batch_size
            )

        # Verify - all tasks should be marked as failed
        assert len(result_map) == 1
        assert not result_map[0].success
        assert isinstance(result_map[0].error, Exception)

    @pytest.mark.asyncio
    async def test_process_edit_tasks_batch_success(self):
        """Test successful processing of a single batch."""
        # Setup
        batch_tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 2),
            EditTask("Test paragraph 2", 1, 1, False, 2),
        ]
        paragraph_processor = AsyncMock()

        with patch.object(
            self.orchestrator, "_process_single_task"
        ) as mock_process_single:
            mock_process_single.side_effect = [
                EditResult(success=True, content="Edited paragraph 1"),
                EditResult(success=True, content="Edited paragraph 2"),
            ]

            # Execute
            results = await self.orchestrator._process_edit_tasks_batch(
                batch_tasks, paragraph_processor
            )

        # Verify
        assert len(results) == 2
        assert results[0].success
        assert results[1].success

    @pytest.mark.asyncio
    async def test_process_edit_tasks_batch_with_exceptions(self):
        """Test batch processing with some tasks throwing exceptions."""
        # Setup
        batch_tasks = [
            EditTask("Test paragraph 1", 0, 0, True, 2),
            EditTask("Test paragraph 2", 1, 1, False, 2),
        ]
        paragraph_processor = AsyncMock()

        with patch.object(
            self.orchestrator, "_process_single_task"
        ) as mock_process_single:
            mock_process_single.side_effect = [
                EditResult(success=True, content="Edited paragraph 1"),
                RuntimeError("Task failed"),
            ]

            # Execute
            results = await self.orchestrator._process_edit_tasks_batch(
                batch_tasks, paragraph_processor
            )

        # Verify
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success
        assert isinstance(results[1].error, RuntimeError)


class TestEditTask:
    """Test cases for EditTask."""

    def test_edit_task_creation(self):
        """Test creating an EditTask."""
        task = EditTask(
            content="test content",
            document_index=5,
            prose_index=2,
            is_first_prose=True,
            total_prose=10,
        )

        assert task.content == "test content"
        assert task.document_index == 5
        assert task.prose_index == 2
        assert task.is_first_prose
        assert task.total_prose == 10


class TestEditResult:
    """Test cases for EditResult dataclass."""

    def test_edit_result_success(self):
        """Test creating a successful EditResult."""
        result = EditResult(success=True, content="edited content")

        assert result.success
        assert result.content == "edited content"
        assert result.error is None

    def test_edit_result_failure(self):
        """Test creating a failed EditResult."""
        error = Exception("Test error")
        result = EditResult(success=False, content="original content", error=error)

        assert not result.success
        assert result.content == "original content"
        assert result.error == error
