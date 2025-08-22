import os
import sys

import pytest

from services.prompts.prompt_manager import (
    PromptManager,
    PromptTemplateFactory,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPrompts:
    """Tests for prompt-related functionality."""

    def test_get_template_invalid_mode(self):
        """Test that get_template raises ValueError for an invalid mode."""
        prompt_manager = PromptManager()
        with pytest.raises(ValueError, match="Unknown editing mode: invalid_mode"):
            prompt_manager.get_template("invalid_mode")

    def test_custom_prompt_with_specific_constraints(self):
        """Test custom prompt creation with specific constraints."""
        factory = PromptTemplateFactory()
        template = factory.create_custom_prompt(
            task_description="<TASK_PLACEHOLDER>",
            specific_constraints="<CONSTRAINTS_PLACEHOLDER>",
        )
        actual_prompt_text = template.format(
            wikitext="<WIKITEXT_PLACEHOLDER>",
        )
        assert "<CONSTRAINTS_PLACEHOLDER>" in actual_prompt_text
        assert "<TASK_PLACEHOLDER>" in actual_prompt_text

    def test_add_and_get_custom_template(self):
        """Test adding and retrieving a custom prompt template."""
        prompt_manager = PromptManager()
        prompt_manager.add_custom_template(
            "custom_task", "Custom task description", "Custom constraints"
        )
        template = prompt_manager.get_template("custom_task")
        assert template is not None
        prompt_text = template.format(
            wikitext="<WIKITEXT_PLACEHOLDER>",
            first_paragraph_specific_instructions="",
        )
        assert "Custom task description" in prompt_text
        assert "Custom constraints" in prompt_text

    def test_list_available_modes(self):
        """Test listing available editing modes."""
        prompt_manager = PromptManager()
        modes = prompt_manager.list_available_modes()
        assert "brevity" in modes
        assert "copyedit" in modes

    def test_custom_prompt_without_specific_constraints(self, snapshot):
        """Test custom prompt creation without specific constraints."""
        factory = PromptTemplateFactory()
        template = factory.create_custom_prompt(task_description="<TASK_PLACEHOLDER>")
        prompt_text = template.format(wikitext="<WIKITEXT_PLACEHOLDER>")
        assert prompt_text.strip() == snapshot

    def test_full_brevity_prompt_structure(self, snapshot):
        """Test the full structure of the brevity prompt for easy inspection."""
        prompt_manager = PromptManager()
        template = prompt_manager.get_template("brevity")
        actual_prompt_text = template.format(wikitext="<WIKITEXT_PLACEHOLDER>")
        assert actual_prompt_text == snapshot
