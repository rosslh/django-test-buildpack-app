"""Abstract base classes and interfaces for the edit module.

This module defines the core interfaces that all components should implement, following
the Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParagraphProcessingResult:
    """Result of a paragraph processing operation."""

    success: bool
    content: str
    failure_reason: Optional[str] = None


@dataclass
class ValidationContext:
    """Context passed through the validation pipeline."""

    paragraph_index: int
    total_paragraphs: int
    is_first_prose: bool
    refs_list: List[Any]
    additional_data: Dict[str, Any]


class IParagraphProcessor(ABC):
    """Interface for processing individual paragraphs."""

    @abstractmethod
    async def process(
        self, content: str, context: ValidationContext
    ) -> ParagraphProcessingResult:
        """Process a single paragraph."""


class IReferenceHandler(ABC):
    """Interface for handling references."""

    @abstractmethod
    def replace_references_with_placeholders(
        self, content: str
    ) -> Tuple[str, List[Any]]:
        """Replace references with placeholders."""

    @abstractmethod
    def restore_references(self, content: str, refs_list: List[Any]) -> str:
        """Restore references from placeholders."""


class IValidator(ABC):
    """Base interface for all validators."""

    @abstractmethod
    def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Validate the edited content against the original.

        Args:
            original: Original content
            edited: Edited content
            context: Additional context for validation

        Returns:
            Tuple of (processed_content, should_revert)
        """

    @abstractmethod
    def get_last_failure_reason(self) -> Optional[str]:
        """Return the reason for the last validation failure."""


class IAsyncValidator(ABC):
    """Base interface for asynchronous validators."""

    @abstractmethod
    async def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Asynchronously validate the edited content.

        Args:
            original: Original content
            edited: Edited content
            context: Additional context for validation

        Returns:
            Tuple of (processed_content, should_revert)
        """

    @abstractmethod
    def get_last_failure_reason(self) -> Optional[str]:
        """Return the reason for the last validation failure."""


class IDocumentProcessor(ABC):
    """Interface for document processing operations."""

    @abstractmethod
    def process(self, content: str) -> List[str]:
        """Process document content into structured items."""


class IContentClassifier(ABC):
    """Interface for content classification."""

    @abstractmethod
    def get_content_type(self, content: str) -> str:
        """Get the type of content."""

    @abstractmethod
    def should_process_with_context(
        self, content: str, index: int, document_items: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Determine if content should be processed considering document context.

        Args:
            content: The content to evaluate
            index: Position of content in the document
            document_items: All items in the document for context

        Returns:
            Tuple of (should_process, skip_reason):
            - should_process: True if content should be processed, False otherwise
            - skip_reason: Explanation if should_process is False, None if should_process is True
        """

    @abstractmethod
    def reset_state(self) -> None:
        """Reset any internal state for processing a new document."""

    @abstractmethod
    def is_in_footer_section(self) -> bool:
        """Check if the classifier is currently in a footer section.

        Returns:
            True if currently processing content in a footer section, False otherwise
        """

    @abstractmethod
    def has_first_prose_been_encountered(self) -> bool:
        """Check if the first prose paragraph has been encountered.

        Returns:
            True if the first prose paragraph has been encountered, False otherwise
        """

    @abstractmethod
    def is_in_lead_section(self) -> bool:
        """Check if the classifier is currently in the lead section.

        Returns:
            True if currently processing content in the lead section, False otherwise
        """


class IEditService(ABC):
    """Interface for the main editing service."""

    @abstractmethod
    async def edit(self, content: str) -> str:
        """Edit the provided content."""


class IValidationPipeline(ABC):
    """Interface for validation pipeline."""

    @abstractmethod
    def add_validator(self, validator: IValidator) -> None:
        """Add a validator to the pipeline."""

    @abstractmethod
    async def validate(
        self, original: str, edited: str, context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Run all validators in the pipeline."""


class IReversionTracker(ABC):
    """Interface for tracking reversions."""

    @abstractmethod
    def record_reversion(self, reversion_type: Any) -> None:
        """Record a reversion event."""

    @abstractmethod
    def get_summary(self) -> str:
        """Get a summary of reversions."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the tracker."""
