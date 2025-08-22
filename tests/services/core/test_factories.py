"""Tests for core.factories module."""

from services.core.factories import (
    ProcessorFactory,
    TrackerFactory,
    ValidatorFactory,
)


class TestValidatorFactory:
    """Test ValidatorFactory methods."""

    def test_create_wikilink_validator(self):
        """Test creating a WikiLink validator."""
        validator = ValidatorFactory.create_wikilink_validator()
        assert validator is not None

    def test_create_reference_validator(self):
        """Test creating a Reference validator."""
        validator = ValidatorFactory.create_reference_validator()
        assert validator is not None

    def test_create_spelling_validator(self):
        """Test creating a Spelling validator."""
        validator = ValidatorFactory.create_spelling_validator()
        assert validator is not None

    def test_create_list_marker_validator(self):
        """Test creating a List Marker validator."""
        validator = ValidatorFactory.create_list_marker_validator()
        assert validator is not None

    def test_create_all_validators(self):
        """Test creating all validators."""
        validators = ValidatorFactory.create_all_validators()
        assert "link_validator" in validators
        assert "reference_validator" in validators
        assert "spelling_validator" in validators
        assert "list_marker_validator" in validators


class TestTrackerFactory:
    """Test TrackerFactory methods."""

    def test_create_reversion_tracker(self):
        """Test creating a reversion tracker."""
        tracker = TrackerFactory.create_reversion_tracker()
        assert tracker is not None
        # Test that it has the expected interface methods
        assert hasattr(tracker, "record_reversion")


class TestProcessorFactory:
    """Test ProcessorFactory methods."""

    def test_create_document_parser(self):
        """Test creating a document parser."""
        parser = ProcessorFactory.create_document_parser()
        assert parser is not None
