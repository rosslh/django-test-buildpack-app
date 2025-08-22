import pytest

from services.validation.validators.template_validator import TemplateValidator


@pytest.fixture
def template_validator():
    """Fixture for TemplateValidator."""
    validator = TemplateValidator()
    return validator


def test_validate_no_change(template_validator):
    """Test that no revert is needed when templates are unchanged."""
    validator = template_validator
    original = "This is a {{template}}."
    edited = "This is a {{template}}."
    assert not validator.validate(original, edited, 0, 1)


def test_validate_template_removed(template_validator):
    """Test that a revert is triggered when a template is removed."""
    validator = template_validator
    original = "This is a {{template}}."
    edited = "This is a ."
    assert validator.validate(original, edited, 0, 1)


def test_validate_template_added(template_validator):
    """Test that a revert is triggered when a template is added."""
    validator = template_validator
    original = "This is a test."
    edited = "This is a {{template}} test."
    assert validator.validate(original, edited, 0, 1)


def test_validate_template_modified(template_validator):
    """Test that a revert is triggered when a template is modified."""
    validator = template_validator
    original = "This is a {{template|arg1}}."
    edited = "This is a {{template|arg2}}."
    assert validator.validate(original, edited, 0, 1)


def test_validate_multiple_templates_reordered(template_validator):
    """Test that reordering templates does not trigger a revert."""
    validator = template_validator
    original = "{{template1}}{{template2}}"
    edited = "{{template2}}{{template1}}"
    assert not validator.validate(original, edited, 0, 1)


def test_validate_with_complex_templates(template_validator):
    """Test with more complex, nested templates."""
    validator = template_validator
    original = "Text with {{template|arg={{nested}}}} and {{template2}}."
    edited = "Text with {{template|arg={{nested}}}} and {{template2}}."
    assert not validator.validate(original, edited, 0, 1)


def test_validate_complex_template_modified(template_validator):
    """Test modification of a complex template."""
    validator = template_validator
    original = "Text with {{template|arg={{nested}}}}."
    edited = "Text with {{template|arg={{changed}}}}."
    assert validator.validate(original, edited, 0, 1)
