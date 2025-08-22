"""Tests for enhanced progress tracking functionality."""

from datetime import datetime
from unittest.mock import patch

import pytest

from services.tracking.progress_tracker import (
    EnhancedProgressTracker,
    ParagraphProgress,
    ProcessingPhase,
)


class TestParagraphProgress:
    """Test the ParagraphProgress dataclass."""

    def test_paragraph_progress_creation(self):
        """Test creating a ParagraphProgress instance."""
        progress = ParagraphProgress(
            index=0,
            phase=ProcessingPhase.PENDING,
            content_preview="Test content",
        )

        assert progress.index == 0
        assert progress.phase == ProcessingPhase.PENDING
        assert progress.content_preview == "Test content"
        assert progress.status is None
        assert progress.started_at is None
        assert progress.completed_at is None

    def test_paragraph_progress_to_dict_minimal(self):
        """Test converting ParagraphProgress to dict with minimal data."""
        progress = ParagraphProgress(
            index=1,
            phase=ProcessingPhase.PENDING,
            content_preview="Test content",
        )

        result = progress.to_dict()
        expected = {
            "index": 1,
            "phase": "pending",
            "content_preview": "Test content",
        }

        assert result == expected

    def test_paragraph_progress_to_dict_complete(self):
        """Test converting ParagraphProgress to dict with all data."""
        started_time = datetime(2025, 7, 14, 10, 30, 0)
        completed_time = datetime(2025, 7, 14, 10, 30, 15)

        progress = ParagraphProgress(
            index=2,
            phase=ProcessingPhase.COMPLETE,
            content_preview="Completed content",
            status="CHANGED",
            started_at=started_time,
            completed_at=completed_time,
        )

        result = progress.to_dict()
        expected = {
            "index": 2,
            "phase": "complete",
            "content_preview": "Completed content",
            "status": "CHANGED",
            "started_at": "2025-07-14T10:30:00Z",
            "completed_at": "2025-07-14T10:30:15Z",
        }

        assert result == expected


class TestEnhancedProgressTracker:
    """Test the EnhancedProgressTracker class."""

    def test_initialization(self):
        """Test tracker initialization with correct number of paragraphs."""
        tracker = EnhancedProgressTracker(total_paragraphs=5)

        assert tracker.total_paragraphs == 5
        assert len(tracker._paragraphs) == 5

        # All paragraphs should start as pending
        for i in range(5):
            assert i in tracker._paragraphs
            assert tracker._paragraphs[i].phase == ProcessingPhase.PENDING
            assert tracker._paragraphs[i].index == i

    def test_get_phase_counts_initial(self):
        """Test getting phase counts after initialization."""
        tracker = EnhancedProgressTracker(total_paragraphs=3)
        counts = tracker.get_phase_counts()

        expected = {
            "pending": 3,
            "pre_processing": 0,
            "llm_processing": 0,
            "post_processing": 0,
            "complete": 0,
        }

        assert counts == expected

    def test_get_progress_percentage_initial(self):
        """Test getting progress percentage after initialization."""
        tracker = EnhancedProgressTracker(total_paragraphs=4)
        assert tracker.get_progress_percentage() == 0

    def test_get_progress_percentage_partial(self):
        """Test getting progress percentage with some completed paragraphs."""
        tracker = EnhancedProgressTracker(total_paragraphs=4)

        # Complete 2 out of 4 paragraphs
        tracker.mark_paragraph_complete(0, "CHANGED")
        tracker.mark_paragraph_complete(1, "UNCHANGED")

        assert tracker.get_progress_percentage() == 50

    def test_get_progress_percentage_complete(self):
        """Test getting progress percentage when all paragraphs are complete."""
        tracker = EnhancedProgressTracker(total_paragraphs=2)

        tracker.mark_paragraph_complete(0, "CHANGED")
        tracker.mark_paragraph_complete(1, "UNCHANGED")

        assert tracker.get_progress_percentage() == 100

    def test_get_progress_percentage_zero_paragraphs(self):
        """Test getting progress percentage with zero paragraphs."""
        tracker = EnhancedProgressTracker(total_paragraphs=0)
        assert tracker.get_progress_percentage() == 0

    def test_update_paragraph_phase_basic(self):
        """Test updating a paragraph's phase."""
        tracker = EnhancedProgressTracker(total_paragraphs=3)

        tracker.update_paragraph_phase(
            1, ProcessingPhase.LLM_PROCESSING, "Test content"
        )

        assert tracker._paragraphs[1].phase == ProcessingPhase.LLM_PROCESSING
        assert tracker._paragraphs[1].content_preview == "Test content"

    def test_update_paragraph_phase_invalid_index(self):
        """Test updating paragraph with invalid index raises error."""
        tracker = EnhancedProgressTracker(total_paragraphs=2)

        with pytest.raises(ValueError, match="Invalid paragraph index: 5"):
            tracker.update_paragraph_phase(5, ProcessingPhase.LLM_PROCESSING)

    def test_update_paragraph_phase_content_truncation(self):
        """Test that content preview is truncated to 100 characters."""
        tracker = EnhancedProgressTracker(total_paragraphs=1)
        long_content = "x" * 150  # 150 characters

        tracker.update_paragraph_phase(0, ProcessingPhase.PRE_PROCESSING, long_content)

        assert len(tracker._paragraphs[0].content_preview) == 100
        assert tracker._paragraphs[0].content_preview == "x" * 100

    @patch("services.tracking.progress_tracker.datetime")
    def test_update_paragraph_phase_timestamps(self, mock_datetime):
        """Test that timestamps are set correctly during phase transitions."""
        mock_time = datetime(2025, 7, 14, 10, 30, 0)
        mock_datetime.utcnow.return_value = mock_time

        tracker = EnhancedProgressTracker(total_paragraphs=1)

        # Move from PENDING to PRE_PROCESSING should set started_at
        tracker.update_paragraph_phase(0, ProcessingPhase.PRE_PROCESSING, "Test")

        assert tracker._paragraphs[0].started_at == mock_time
        assert tracker._paragraphs[0].completed_at is None

        # Move to COMPLETE should set completed_at
        mock_time_complete = datetime(2025, 7, 14, 10, 30, 15)
        mock_datetime.utcnow.return_value = mock_time_complete

        tracker.update_paragraph_phase(0, ProcessingPhase.COMPLETE, status="CHANGED")

        assert tracker._paragraphs[0].started_at == mock_time
        assert tracker._paragraphs[0].completed_at == mock_time_complete
        assert tracker._paragraphs[0].status == "CHANGED"

    def test_mark_paragraph_started(self):
        """Test marking a paragraph as started."""
        tracker = EnhancedProgressTracker(total_paragraphs=2)

        tracker.mark_paragraph_started(0, "Starting content")

        assert tracker._paragraphs[0].phase == ProcessingPhase.PRE_PROCESSING
        assert tracker._paragraphs[0].content_preview == "Starting content"

    def test_mark_paragraph_llm_processing(self):
        """Test marking a paragraph as LLM processing."""
        tracker = EnhancedProgressTracker(total_paragraphs=2)

        tracker.mark_paragraph_llm_processing(1)

        assert tracker._paragraphs[1].phase == ProcessingPhase.LLM_PROCESSING

    def test_mark_paragraph_post_processing(self):
        """Test marking a paragraph as post-processing."""
        tracker = EnhancedProgressTracker(total_paragraphs=2)

        tracker.mark_paragraph_post_processing(0)

        assert tracker._paragraphs[0].phase == ProcessingPhase.POST_PROCESSING

    def test_mark_paragraph_complete(self):
        """Test marking a paragraph as complete."""
        tracker = EnhancedProgressTracker(total_paragraphs=2)

        tracker.mark_paragraph_complete(1, "UNCHANGED")

        assert tracker._paragraphs[1].phase == ProcessingPhase.COMPLETE
        assert tracker._paragraphs[1].status == "UNCHANGED"

    def test_get_progress_data_complete(self):
        """Test getting complete progress data."""
        tracker = EnhancedProgressTracker(total_paragraphs=3)

        # Set up different phases
        tracker.mark_paragraph_started(0, "First paragraph")
        tracker.mark_paragraph_llm_processing(1)
        tracker.mark_paragraph_complete(2, "CHANGED")

        progress_data = tracker.get_progress_data()

        assert progress_data["total_paragraphs"] == 3
        assert progress_data["progress_percentage"] == 33  # 1 out of 3 complete

        expected_counts = {
            "pending": 0,
            "pre_processing": 1,
            "llm_processing": 1,
            "post_processing": 0,
            "complete": 1,
        }
        assert progress_data["phase_counts"] == expected_counts

        # Check paragraphs are sorted by index
        assert len(progress_data["paragraphs"]) == 3
        assert progress_data["paragraphs"][0]["index"] == 0
        assert progress_data["paragraphs"][1]["index"] == 1
        assert progress_data["paragraphs"][2]["index"] == 2

        # Check specific paragraph data
        assert progress_data["paragraphs"][0]["phase"] == "pre_processing"
        assert progress_data["paragraphs"][1]["phase"] == "llm_processing"
        assert progress_data["paragraphs"][2]["phase"] == "complete"
        assert progress_data["paragraphs"][2]["status"] == "CHANGED"

    def test_thread_safety_basic(self):
        """Test basic thread safety of operations."""
        import threading
        import time

        tracker = EnhancedProgressTracker(total_paragraphs=10)
        results = []

        def update_paragraphs(start_idx):
            for i in range(start_idx, start_idx + 2):
                tracker.mark_paragraph_started(i, f"Content {i}")
                time.sleep(0.001)  # Small delay to encourage race conditions
                tracker.mark_paragraph_complete(i, "CHANGED")
                results.append(i)

        # Create threads that update different paragraphs
        threads = []
        for start in [0, 2, 4, 6, 8]:
            thread = threading.Thread(target=update_paragraphs, args=(start,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all paragraphs were updated
        assert len(results) == 10

        # Check final state
        final_data = tracker.get_progress_data()
        assert final_data["progress_percentage"] == 100
        assert final_data["phase_counts"]["complete"] == 10
