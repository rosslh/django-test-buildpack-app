"""Test cases for main constants module."""

from services.core.constants import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    FOOTER_HEADINGS,
    MIN_PARAGRAPH_LENGTH,
    NON_PROSE_PREFIXES,
    UNCHANGED_MARKER,
    GeminiModel,
    LLMProvider,
    OpenAIModel,
)


def test_llm_provider_enum():
    """Test LLM provider enum values."""
    assert LLMProvider.GOOGLE.value == "google"
    assert LLMProvider.OPENAI.value == "openai"


def test_gemini_model_enum():
    """Test Gemini model enum and default."""
    assert isinstance(DEFAULT_GEMINI_MODEL, str)
    assert DEFAULT_GEMINI_MODEL == GeminiModel.GEMINI_2_5_FLASH.value


def test_openai_model_enum():
    """Test OpenAI model enum and default."""
    assert isinstance(DEFAULT_OPENAI_MODEL, str)
    assert DEFAULT_OPENAI_MODEL == OpenAIModel.GPT_4O_MINI.value


def test_processing_constants():
    """Test processing configuration constants."""
    assert isinstance(MIN_PARAGRAPH_LENGTH, int)
    assert MIN_PARAGRAPH_LENGTH > 0
    assert isinstance(UNCHANGED_MARKER, str)
    assert UNCHANGED_MARKER == "<UNCHANGED>"


def test_non_prose_prefixes():
    """Test non-prose prefixes set."""
    assert isinstance(NON_PROSE_PREFIXES, set)
    assert "==" in NON_PROSE_PREFIXES
    assert "[[Category:" in NON_PROSE_PREFIXES
    assert "{{" in NON_PROSE_PREFIXES


def test_footer_headings():
    """Test footer headings set."""
    assert isinstance(FOOTER_HEADINGS, set)
    assert "see also" in FOOTER_HEADINGS
    assert "references" in FOOTER_HEADINGS
    assert "external links" in FOOTER_HEADINGS
