"""Configuration and constants for the Wiki Editor."""

import os
from enum import Enum

# Processing configuration
MIN_PARAGRAPH_LENGTH = 48
UNCHANGED_MARKER = "<UNCHANGED>"

# Concurrency configuration
# Conservative defaults optimized for low-resource servers (0.5 cores, 512MB RAM)
# Celery worker concurrency controls the number of concurrent batch tasks
# Each batch processes multiple paragraphs to reduce task creation overhead
DEFAULT_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "1"))

# Paragraph batching configuration
# Number of paragraphs to process in each Celery task
# Reduces task creation overhead while maintaining parallelism
DEFAULT_PARAGRAPH_BATCH_SIZE = int(os.environ.get("CELERY_PARAGRAPH_BATCH_SIZE", "3"))

# Wiki markup prefixes that indicate non-prose content
NON_PROSE_PREFIXES = {
    "==",  # Headers
    "[[Category:",
    "=",
    "[[File:",
    "<blockquote>",
    "|",
    "}",
    "!",
    ":",
    "<!--",
    "__",
    "#REDIRECT",
    " ",
    "\t",
    "{",
    "<div",
    "<table",
    "<span",
    "{{",  # Templates
    "*",  # List items
    "#",  # Numbered list items
    "<ref>",  # Citations only
}

FOOTER_HEADINGS = {
    "see also",
    "references",
    "notes",
    "external links",
    "further reading",
    "bibliography",
}

# Meta commentary words that indicate LLM is providing commentary instead of edits
META_COMMENTARY_WORDS = {
    "i",  # "I could not identify any changes"
    "me",  # "Let me help you with this"
    "edit",  # "This edit improves the text"
    "please",  # "Please review this text"
    "wikitext",  # "I cannot find any wikitext issues"
    "sorry",  # "Sorry, I cannot help"
    "apologize",  # "I apologize but I cannot"
}


class LLMProvider(Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    PERPLEXITY = "perplexity"


class GeminiModel(Enum):
    GEMINI_2_5_FLASH = "models/gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "models/gemini-2.5-flash-lite-preview-06-17"


class OpenAIModel(Enum):
    GPT_4O_MINI = "gpt-4o-mini"  # TODO: verify organization


class AnthropicModel(Enum):
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"


class MistralModel(Enum):
    MISTRAL_SMALL = "mistral-small-latest"


class PerplexityModel(Enum):
    LLAMA_3_1_SONAR_SMALL = "llama-3.1-sonar-small-128k-online"


DEFAULT_GEMINI_MODEL = GeminiModel.GEMINI_2_5_FLASH.value
DEFAULT_OPENAI_MODEL = OpenAIModel.GPT_4O_MINI.value
DEFAULT_ANTHROPIC_MODEL = AnthropicModel.CLAUDE_3_5_HAIKU.value
DEFAULT_MISTRAL_MODEL = MistralModel.MISTRAL_SMALL.value
DEFAULT_PERPLEXITY_MODEL = PerplexityModel.LLAMA_3_1_SONAR_SMALL.value
