"""Enhanced progress tracking for concurrent paragraph processing."""

import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class ProcessingPhase(Enum):
    """Enum for paragraph processing phases."""

    PENDING = "pending"
    PRE_PROCESSING = "pre_processing"
    LLM_PROCESSING = "llm_processing"
    POST_PROCESSING = "post_processing"
    COMPLETE = "complete"


@dataclass
class ParagraphProgress:
    """Tracks progress for a single paragraph."""

    index: int
    phase: ProcessingPhase
    content_preview: str
    status: Optional[str] = None  # Only set when phase is COMPLETE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = {
            "index": self.index,
            "phase": self.phase.value,
            "content_preview": self.content_preview,
        }

        if self.status is not None:
            data["status"] = self.status

        if self.started_at:
            data["started_at"] = self.started_at.isoformat() + "Z"

        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat() + "Z"

        return data


class EnhancedProgressTracker:
    """Thread-safe progress tracker for concurrent paragraph processing."""

    def __init__(self, total_paragraphs: int):
        self.total_paragraphs = total_paragraphs
        self._paragraphs: Dict[int, ParagraphProgress] = {}
        self._lock = threading.Lock()

        # Initialize all paragraphs as pending
        for i in range(total_paragraphs):
            self._paragraphs[i] = ParagraphProgress(
                index=i,
                phase=ProcessingPhase.PENDING,
                content_preview="",
            )

    def update_paragraph_phase(
        self,
        paragraph_index: int,
        phase: ProcessingPhase,
        content_preview: Optional[str] = None,
        status: Optional[str] = None,
    ):
        """Update the phase of a specific paragraph in a thread-safe manner."""
        with self._lock:
            if paragraph_index not in self._paragraphs:
                raise ValueError(f"Invalid paragraph index: {paragraph_index}")

            paragraph = self._paragraphs[paragraph_index]
            old_phase = paragraph.phase
            paragraph.phase = phase

            if content_preview:
                # Truncate content preview to first 100 characters
                paragraph.content_preview = content_preview[:100]

            # Set timestamps
            current_time = datetime.utcnow()
            if (
                old_phase == ProcessingPhase.PENDING
                and phase != ProcessingPhase.PENDING
            ):
                paragraph.started_at = current_time

            if phase == ProcessingPhase.COMPLETE:
                paragraph.completed_at = current_time
                if status:
                    paragraph.status = status

    def get_phase_counts(self) -> Dict[str, int]:
        """Get count of paragraphs in each phase."""
        with self._lock:
            counts = {phase.value: 0 for phase in ProcessingPhase}
            for paragraph in self._paragraphs.values():
                counts[paragraph.phase.value] += 1
            return counts

    def get_progress_percentage(self) -> int:
        """Calculate overall progress percentage."""
        with self._lock:
            completed_count = sum(
                1
                for p in self._paragraphs.values()
                if p.phase == ProcessingPhase.COMPLETE
            )
            return (
                round((completed_count / self.total_paragraphs) * 100)
                if self.total_paragraphs > 0
                else 0
            )

    def get_progress_data(self) -> dict:
        """Get complete progress data for API response."""
        with self._lock:
            # Calculate phase counts directly to avoid nested locking
            counts = {phase.value: 0 for phase in ProcessingPhase}
            completed_count = 0
            for paragraph in self._paragraphs.values():
                counts[paragraph.phase.value] += 1
                if paragraph.phase == ProcessingPhase.COMPLETE:
                    completed_count += 1

            # Calculate progress percentage directly
            progress_percentage = (
                round((completed_count / self.total_paragraphs) * 100)
                if self.total_paragraphs > 0
                else 0
            )

            # Sort paragraphs by index for consistent ordering
            paragraphs = [
                self._paragraphs[i].to_dict() for i in sorted(self._paragraphs.keys())
            ]

            return {
                "total_paragraphs": self.total_paragraphs,
                "progress_percentage": progress_percentage,
                "phase_counts": counts,
                "paragraphs": paragraphs,
            }

    def mark_paragraph_started(self, paragraph_index: int, content: str):
        """Mark a paragraph as starting pre-processing."""
        self.update_paragraph_phase(
            paragraph_index, ProcessingPhase.PRE_PROCESSING, content
        )

    def mark_paragraph_llm_processing(self, paragraph_index: int):
        """Mark a paragraph as being processed by LLM."""
        self.update_paragraph_phase(paragraph_index, ProcessingPhase.LLM_PROCESSING)

    def mark_paragraph_post_processing(self, paragraph_index: int):
        """Mark a paragraph as in post-processing phase."""
        self.update_paragraph_phase(paragraph_index, ProcessingPhase.POST_PROCESSING)

    def mark_paragraph_complete(self, paragraph_index: int, status: str):
        """Mark a paragraph as complete with final status."""
        self.update_paragraph_phase(
            paragraph_index, ProcessingPhase.COMPLETE, status=status
        )
