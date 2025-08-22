"""Unit tests for the BaseValidator."""


class TestBaseValidator:
    """Test cases for BaseValidator class."""

    def test_base_validator_instantiation(self):
        """Test that BaseValidator can be instantiated."""
        from services.validation.base_validator import BaseValidator

        validator = BaseValidator()
        assert isinstance(validator, BaseValidator)
