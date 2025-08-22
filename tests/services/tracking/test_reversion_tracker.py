"""Tests for the reversion tracking functionality."""

import pytest

from services.tracking.reversion_tracker import ReversionTracker, ReversionType


class TestReversionType:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert ReversionType.LINK_VALIDATION_FAILURE.value == "link_validation_failure"
        assert (
            ReversionType.REFERENCE_VALIDATION_FAILURE.value
            == "reference_validation_failure"
        )
        assert ReversionType.ADDED_CONTENT_VIOLATION.value == "added_content_violation"
        assert (
            ReversionType.REFERENCE_CONTENT_CHANGE.value == "reference_content_change"
        )
        assert ReversionType.API_ERROR.value == "api_error"
        assert ReversionType.UNEXPECTED_ERROR.value == "unexpected_error"

    def test_enum_count(self):
        """Test that we have the expected number of reversion types."""
        assert len(ReversionType) == 6


class TestReversionTracker:
    def test_initial_state(self):
        """Test that tracker initializes with all counters at zero."""
        tracker = ReversionTracker()
        for reversion_type in ReversionType:
            assert tracker.get_count(reversion_type) == 0
        summary = tracker.get_summary()
        assert summary == ""

    def test_record_reversion_with_enum(self):
        """Test recording reversions using the enum-based method."""
        tracker = ReversionTracker()

        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)
        assert tracker.get_count(ReversionType.LINK_VALIDATION_FAILURE) == 1

        tracker.record_reversion(ReversionType.API_ERROR)
        assert tracker.get_count(ReversionType.API_ERROR) == 1

    def test_record_reversion_invalid_type(self):
        """Test that recording an invalid reversion type raises ValueError."""
        tracker = ReversionTracker()

        # This should raise ValueError since we're not passing a valid enum value
        with pytest.raises(ValueError, match="Unknown reversion type"):
            tracker.record_reversion("invalid_type")  # type: ignore

    def test_get_count_method(self):
        """Test the get_count method for specific reversion types."""
        tracker = ReversionTracker()

        # Initially all counts should be 0
        assert tracker.get_count(ReversionType.LINK_VALIDATION_FAILURE) == 0
        assert tracker.get_count(ReversionType.API_ERROR) == 0

        # Record some reversions
        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)
        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)
        tracker.record_reversion(ReversionType.API_ERROR)

        # Check counts
        assert tracker.get_count(ReversionType.LINK_VALIDATION_FAILURE) == 2
        assert tracker.get_count(ReversionType.API_ERROR) == 1
        assert tracker.get_count(ReversionType.REFERENCE_VALIDATION_FAILURE) == 0

    def test_get_summary_no_reversions(self):
        """Test summary when there are no reversions."""
        tracker = ReversionTracker()
        assert tracker.get_summary() == ""

    def test_get_summary_with_all_error_types(self):
        """Test summary with all types of reversions."""
        tracker = ReversionTracker()
        for reversion_type in ReversionType:
            tracker.record_reversion(reversion_type)

        summary = tracker.get_summary()
        assert f"{len(ReversionType)} paragraph(s) had unrecoverable errors" in summary
        assert "Link validation failures: 1" in summary
        assert "Reference validation failures: 1" in summary
        assert "Added content violations: 1" in summary
        assert "Reference content changes: 1" in summary
        assert "API errors: 1" in summary
        assert "Unexpected errors: 1" in summary

    def test_get_summary_with_multiple_of_one_type(self):
        """Test summary with multiple errors of one type."""
        tracker = ReversionTracker()
        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)
        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)
        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)

        summary = tracker.get_summary()
        assert "3 paragraph(s) had unrecoverable errors" in summary
        assert "Link validation failures: 3" in summary
        assert "Reference validation failures:" not in summary

    def test_reset(self):
        """Test reset functionality."""
        tracker = ReversionTracker()
        tracker.record_reversion(ReversionType.LINK_VALIDATION_FAILURE)
        tracker.record_reversion(ReversionType.API_ERROR)

        summary = tracker.get_summary()
        assert "2 paragraph(s) had unrecoverable errors" in summary

        tracker.reset()
        summary = tracker.get_summary()
        assert summary == ""
        assert tracker.get_count(ReversionType.LINK_VALIDATION_FAILURE) == 0
        assert tracker.get_count(ReversionType.API_ERROR) == 0
