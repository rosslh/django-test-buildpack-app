"""Edit orchestrator for coordinating the wiki editing workflow.

This module separates the orchestration logic from the actual editing logic, following
the Single Responsibility Principle.
"""

import asyncio
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from asgiref.sync import sync_to_async

from services.core.constants import DEFAULT_WORKER_CONCURRENCY
from services.core.interfaces import (
    IContentClassifier,
    IDocumentProcessor,
    IParagraphProcessor,
    IReferenceHandler,
    IReversionTracker,
    ValidationContext,
)
from services.tracking.progress_tracker import EnhancedProgressTracker


@dataclass
class EditTask:
    """Represents a single editing task."""

    content: str
    document_index: int
    prose_index: int
    is_first_prose: bool
    total_prose: int


@dataclass
class SkippedItem:
    """Represents an item that was skipped during processing."""

    content: str
    document_index: int
    content_type: str
    skip_reason: str


@dataclass
class EditResult:
    """Result of an editing operation."""

    success: bool
    content: str
    error: Optional[BaseException] = None
    failure_reason: Optional[str] = (
        None  # Specific reason for failure (validation, etc.)
    )


@dataclass
class ParagraphResult:
    """Result of a paragraph editing operation."""

    before: str
    after: str
    status: str  # 'UNCHANGED' | 'CHANGED' | 'REJECTED' | 'SKIPPED' | 'ERRORED'
    status_details: str  # Explanation of why the edit had this status


class EditOrchestrator:
    """Orchestrates the editing workflow.

    This class is responsible for coordinating the high-level editing process,
    delegating specific tasks to specialized components.
    """

    def __init__(
        self,
        document_processor: IDocumentProcessor,
        content_classifier: IContentClassifier,
        reversion_tracker: IReversionTracker,
        reference_handler: IReferenceHandler,
        max_concurrent_requests: int = DEFAULT_WORKER_CONCURRENCY,
    ):
        self.document_processor = document_processor
        self.content_classifier = content_classifier
        self.reversion_tracker = reversion_tracker
        self.reference_handler = reference_handler

        # Note: max_concurrent_requests parameter is kept for backward compatibility
        # but LLM rate limiting is now handled by LangChain and the providers

        # Enhanced progress tracking
        self._progress_tracker: Optional[EnhancedProgressTracker] = None
        self._enhanced_progress_callback: Optional[Callable] = None

    async def orchestrate_edit_structured(
        self,
        text: str,
        paragraph_processor: IParagraphProcessor,
        enhanced_progress_callback=None,
    ) -> List[ParagraphResult]:
        self._reset_tracking()
        document_items = self._parse_document_structure(text)
        edit_tasks, skipped_items = self._analyze_and_create_edit_tasks(document_items)

        # Initialize enhanced progress tracking if callback provided
        if enhanced_progress_callback:
            self._progress_tracker = EnhancedProgressTracker(len(edit_tasks))
            self._enhanced_progress_callback = enhanced_progress_callback
            # Send initial progress update
            await sync_to_async(enhanced_progress_callback)(
                self._progress_tracker.get_progress_data()
            )

        paragraph_results = await self._process_and_create_results(
            edit_tasks,
            skipped_items,
            document_items,
            paragraph_processor,
        )
        self._display_summary()
        return paragraph_results

    async def orchestrate_edit_structured_batched(
        self,
        text: str,
        paragraph_processor: IParagraphProcessor,
        enhanced_progress_callback=None,
        batch_size: int = 5,
    ) -> List[ParagraphResult]:
        """Orchestrate editing with batched paragraph processing to reduce task overhead.

        Args:
            text: The text to edit
            paragraph_processor: The processor to use for paragraph editing
            enhanced_progress_callback: Optional callback for progress updates
            batch_size: Number of paragraphs to process per batch

        Returns:
            List of ParagraphResult objects with before/after content and status
        """
        self._reset_tracking()
        document_items = self._parse_document_structure(text)
        edit_tasks, skipped_items = self._analyze_and_create_edit_tasks(document_items)

        # Initialize enhanced progress tracking if callback provided
        if enhanced_progress_callback:
            self._progress_tracker = EnhancedProgressTracker(len(edit_tasks))
            self._enhanced_progress_callback = enhanced_progress_callback
            # Send initial progress update
            await sync_to_async(enhanced_progress_callback)(
                self._progress_tracker.get_progress_data()
            )

        paragraph_results = await self._process_and_create_results_batched(
            edit_tasks,
            skipped_items,
            document_items,
            paragraph_processor,
            batch_size,
        )
        self._display_summary()
        return paragraph_results

    def _reset_tracking(self):
        self.reversion_tracker.reset()

    def _parse_document_structure(self, text):
        try:
            document_items = self.document_processor.process(text)
            return document_items
        except Exception:
            raise

    def _analyze_and_create_edit_tasks(self, document_items):
        try:
            edit_tasks, skipped_items = self._create_edit_tasks_and_skipped_items(
                document_items
            )
            return edit_tasks, skipped_items
        except Exception:
            raise

    def _create_result_for_processed_item(
        self, item: str, edit_result: EditResult
    ) -> ParagraphResult:
        """Create a ParagraphResult for an item that was processed."""
        if edit_result.success:
            if edit_result.content != item:
                status = "CHANGED"
                status_details = (
                    "Content was successfully edited by AI and passed validation"
                )
            else:
                status = "UNCHANGED"
                status_details = "Content was processed but no changes were made"
            return ParagraphResult(
                before=item,
                after=edit_result.content,
                status=status,
                status_details=status_details,
            )
        else:
            # This is a processed item that failed - could be rejected or errored
            if edit_result.error:
                status = "ERRORED"
                status_details = (
                    f"Error during task processing: {type(edit_result.error).__name__}"
                )
            else:
                status = "REJECTED"
                if edit_result.failure_reason:
                    status_details = (
                        f"Edit failed validation: {edit_result.failure_reason}"
                    )
                else:
                    status_details = (
                        "Edit was made but failed validation and was reverted"
                    )
            return ParagraphResult(
                before=item, after=item, status=status, status_details=status_details
            )

    def _create_result_for_skipped_item(
        self, skipped_item: SkippedItem
    ) -> ParagraphResult:
        """Create a ParagraphResult for an item that was skipped."""
        return ParagraphResult(
            before=skipped_item.content,
            after=skipped_item.content,
            status="SKIPPED",
            status_details=skipped_item.skip_reason,
        )

    async def _process_and_create_results(
        self,
        edit_tasks,
        skipped_items,
        document_items,
        paragraph_processor,
    ):
        edit_result_map = await self._execute_edit_tasks(
            edit_tasks, paragraph_processor
        )
        skipped_item_map = {item.document_index: item for item in skipped_items}
        return self._create_paragraph_results(
            document_items, edit_result_map, skipped_item_map
        )

    async def _process_and_create_results_batched(
        self,
        edit_tasks,
        skipped_items,
        document_items,
        paragraph_processor,
        batch_size: int,
    ):
        """Process tasks in batches and create results."""
        edit_result_map = await self._execute_edit_tasks_batched(
            edit_tasks, paragraph_processor, batch_size
        )
        skipped_item_map = {item.document_index: item for item in skipped_items}
        return self._create_paragraph_results(
            document_items, edit_result_map, skipped_item_map
        )

    async def _execute_edit_tasks(self, edit_tasks, paragraph_processor):
        """Execute edit tasks and return a map of results."""
        edit_result_map = {}
        if edit_tasks:
            try:
                edit_results = await self._process_edit_tasks(
                    edit_tasks, paragraph_processor
                )
                for task, result in zip(edit_tasks, edit_results, strict=False):
                    # Handle cases where the result is an exception from `gather`
                    if isinstance(result, BaseException):
                        result = EditResult(
                            success=False, content=task.content, error=result
                        )
                    edit_result_map[task.document_index] = result
            except Exception as e:
                # Create error results for all tasks if gathering fails
                for task in edit_tasks:
                    edit_result_map[task.document_index] = EditResult(
                        success=False, content=task.content, error=e
                    )
        return edit_result_map

    async def _execute_edit_tasks_batched(
        self, edit_tasks, paragraph_processor, batch_size: int
    ):
        """Execute edit tasks in batches and return a map of results."""
        edit_result_map: dict = {}
        if not edit_tasks:
            return edit_result_map

        # Split tasks into batches
        task_batches = [
            edit_tasks[i : i + batch_size]
            for i in range(0, len(edit_tasks), batch_size)
        ]

        try:
            # Process all batches concurrently
            batch_results = await asyncio.gather(
                *[
                    self._process_edit_tasks_batch(batch, paragraph_processor)
                    for batch in task_batches
                ],
                return_exceptions=True,
            )

            # Combine results from all batches
            for batch, batch_result in zip(task_batches, batch_results, strict=False):
                if isinstance(batch_result, BaseException):
                    # If a batch failed, mark all tasks in that batch as failed
                    for task in batch:
                        edit_result_map[task.document_index] = EditResult(
                            success=False, content=task.content, error=batch_result
                        )
                else:
                    # Add successful batch results to the result map
                    for task, result in zip(batch, batch_result, strict=False):
                        if isinstance(result, BaseException):
                            result = EditResult(
                                success=False, content=task.content, error=result
                            )
                        edit_result_map[task.document_index] = result

        except Exception as e:
            # Create error results for all tasks if something goes wrong
            for task in edit_tasks:
                edit_result_map[task.document_index] = EditResult(
                    success=False, content=task.content, error=e
                )

        return edit_result_map

    async def _process_edit_tasks_batch(
        self, batch_tasks, paragraph_processor: IParagraphProcessor
    ):
        """Process a single batch of edit tasks."""
        # Create a coroutine for each task in the batch
        coroutines = [
            self._process_single_task(task, paragraph_processor) for task in batch_tasks
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)
        processed_results = []
        for result in results:
            if isinstance(result, BaseException):
                processed_results.append(
                    EditResult(success=False, content="", error=result)
                )
            else:
                processed_results.append(result)
        return processed_results

    def _create_paragraph_results(
        self, document_items, edit_result_map, skipped_item_map
    ):
        """Create paragraph results from processed items."""
        paragraph_results = []

        for i, item in enumerate(document_items):
            paragraph_result = self._create_single_paragraph_result(
                i, item, edit_result_map, skipped_item_map
            )
            paragraph_results.append(paragraph_result)

        return paragraph_results

    def _create_single_paragraph_result(
        self, index, item, edit_result_map, skipped_item_map
    ):
        """Create a single paragraph result based on the processing outcome."""
        if index in edit_result_map:
            edit_result = edit_result_map[index]
            return self._create_result_for_processed_item(item, edit_result)
        elif index in skipped_item_map:
            skipped_item = skipped_item_map[index]
            return self._create_result_for_skipped_item(skipped_item)
        else:
            # This shouldn't happen in normal operation, but handle it gracefully
            return ParagraphResult(
                before=item,
                after=item,
                status="SKIPPED",
                status_details="Item not processed for unknown reason",
            )

    def _display_summary(self):
        summary = self.reversion_tracker.get_summary()
        if summary:
            print(summary)

    def _create_edit_tasks_and_skipped_items(
        self, document_items: List[str]
    ) -> Tuple[List[EditTask], List[SkippedItem]]:
        """Create edit tasks and track skipped items with their reasons."""
        # Reset classifier state for new document
        self.content_classifier.reset_state()

        tasks = []
        skipped_items = []
        prose_index = 0

        for i, item in enumerate(document_items):
            content_type = self.content_classifier.get_content_type(item)

            should_process, skip_reason = (
                self.content_classifier.should_process_with_context(
                    item, i, document_items
                )
            )
            if should_process:
                tasks.append(
                    EditTask(
                        content=item.strip(),
                        document_index=i,
                        prose_index=prose_index,
                        is_first_prose=False,  # No longer tracked here
                        total_prose=0,  # Will be updated after all tasks are created
                    )
                )
                prose_index += 1
            else:
                # Skip reason is provided directly by the classifier
                skipped_items.append(
                    SkippedItem(
                        content=item,
                        document_index=i,
                        content_type=content_type,
                        skip_reason=skip_reason or "Unknown reason",
                    )
                )

        # Update total prose count
        for task in tasks:
            task.total_prose = len(tasks)

        return tasks, skipped_items

    async def _process_edit_tasks(
        self, tasks: List[EditTask], paragraph_processor: IParagraphProcessor
    ) -> List[EditResult]:
        """Process a list of edit tasks."""
        # Create a coroutine for each task
        coroutines = [
            self._process_single_task(task, paragraph_processor) for task in tasks
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)
        processed_results = []
        for result in results:
            if isinstance(result, BaseException):
                processed_results.append(
                    EditResult(success=False, content="", error=result)
                )
            else:
                processed_results.append(result)
        return processed_results

    async def _process_single_task(
        self, task: EditTask, paragraph_processor: IParagraphProcessor
    ) -> EditResult:
        """Process a single edit task with enhanced progress tracking."""
        try:
            await self._update_progress(task.prose_index, "started", task.content)
            context = self._create_validation_context(task)

            await self._update_progress(task.prose_index, "llm_processing")
            process_result = await paragraph_processor.process(task.content, context)

            await self._update_progress(task.prose_index, "post_processing")

            if process_result.success:
                status = (
                    "CHANGED" if process_result.content != task.content else "UNCHANGED"
                )
                await self._update_progress(task.prose_index, "complete", status=status)
                return EditResult(success=True, content=process_result.content)
            else:
                await self._update_progress(
                    task.prose_index, "complete", status="REJECTED"
                )
                return EditResult(
                    success=False,
                    content=task.content,
                    failure_reason=process_result.failure_reason,
                )
        except Exception as e:
            await self._update_progress(task.prose_index, "complete", status="ERRORED")
            return EditResult(success=False, content=task.content, error=e)

    async def _update_progress(
        self,
        prose_index: int,
        stage: str,
        content: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        """Update progress tracking for a paragraph."""
        if not self._progress_tracker:
            return

        if stage == "started" and content is not None:
            self._progress_tracker.mark_paragraph_started(prose_index, content)
        elif stage == "llm_processing":
            self._progress_tracker.mark_paragraph_llm_processing(prose_index)
        elif stage == "post_processing":
            self._progress_tracker.mark_paragraph_post_processing(prose_index)
        elif stage == "complete" and status is not None:
            self._progress_tracker.mark_paragraph_complete(prose_index, status)

        if self._enhanced_progress_callback:
            await sync_to_async(self._enhanced_progress_callback)(
                self._progress_tracker.get_progress_data()
            )

    def _create_validation_context(self, task: EditTask) -> ValidationContext:
        """Create a validation context for a given task."""
        text_with_placeholders, refs_list = (
            self.reference_handler.replace_references_with_placeholders(task.content)
        )

        return ValidationContext(
            paragraph_index=task.prose_index,
            total_paragraphs=task.total_prose,
            is_first_prose=task.is_first_prose,
            refs_list=refs_list,
            additional_data={
                "document_index": task.document_index,
                "original_content": task.content,
                "text_with_placeholders": text_with_placeholders,
            },
        )

    def _assemble_document(
        self,
        original_items: List[str],
        tasks: List[EditTask],
        results: List[EditResult],
    ) -> str:
        """Assemble the final document from results."""
        final_items = original_items.copy()

        for task, result in zip(tasks, results, strict=False):
            if result.success:
                final_items[task.document_index] = result.content

        return "\n".join(final_items)
