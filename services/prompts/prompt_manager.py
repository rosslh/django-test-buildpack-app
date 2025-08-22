"""Prompt templates for Wiki editing operations."""

from typing import List

from langchain.prompts import PromptTemplate

# Critical constraints used in prompts
SHARED_CRITICAL_CONSTRAINTS = """== Critical Preservation Rules ==

Protected Content - PRESERVE EXACTLY:
* Direct quotes, book titles, media titles, URLs
* Factual information: names, numbers, dates, ISBNs, specific details
* Templates: anything in `{{{{...}}}}` markup (e.g., `{{{{sfn}}}}` or `{{{{ref}}}}`)
* Date formatting (e.g., "5 June" vs "June 5")
* Regional spelling variants (e.g., "colour" vs "color")
* Degrees of certainty/attribution (e.g., "suggests" vs "determined")
* All wikitext markup and special characters (even if apparently invalid)
* Non-English text

Links (e.g., `[[Page Name]]` or `[[Page Name|Display Text]]`) - PRESERVE EXACTLY:
* The `[[...]]` syntax is sacred and MUST NOT be removed or altered
* Do not remove, add, or change where a link points
* You may edit the display text (after the `|`) for style, but MUST NOT change the link target page
* Advanced link syntax should be preserved (e.g., `[[copyright]]ed`, `[[Seattle, Washington|]]`, or `[[:de:Deutschland|Germany]]`)

References (e.g., `<ref name="0" />`) - PRESERVE EXACTLY:
* Preserve all `<ref>` tags
* Do not change the reference format - keep it XML-like
* Never add, remove, or move references
* Ensure references follow the same text as in the original
* Do not invent new reference names (e.g., `<ref name="1" />`)
* Preserve the exact number and format of references

Quotations - PRESERVE EXACTLY:
* Do not add, remove, truncate, paraphrase, or otherwise modify quotations
* Do not combine quoted statements - even from the same source
* Keep multiple related quotations or excerpts separated
* Don't replace apostrophes used for ''italics'' or '''bold''' with quotation marks

Relationships & Sequences - PRESERVE EXACTLY:
* Preserve relationships between entities and chronological/causal order
* Multi-part relationships (e.g., "A succeeded B as C's superior") must remain intact

Safety Protocol:
* NO new links (anything in `[[...]]` markup), but display text can be refined
* NO new templates (anything in `{{{{...}}}}` markup)
* NO new content elements (images, list items, tables)
* If no safe improvements possible, return only <UNCHANGED>
* LINK INTEGRITY: Never add, alter, or remove link destinations; only modify display text in existing piped links"""


BREVITY_SPECIFIC_CONSTRAINTS = """== Brevity Guidelines ==

Conciseness Rules:
* NEVER abbreviate terms written in full
* Preserve exact meaning over brevity when simplifying complex sentences
* Avoid awkward/overly condensed phrasing - favor natural, idiomatic language
* We care about the brevity of the display text, not concise wikitext markup"""


class PromptTemplateFactory:
    """Factory for creating different types of editing prompts."""

    @staticmethod
    def create_brevity_prompt() -> PromptTemplate:
        """Creates a prompt template for brevity editing."""
        return PromptTemplate.from_template(
            f"""You are an expert editor specializing in concise, clear writing.

== Your Task ==

Edit the following wikitext for brevity while preserving all meaning.

* Remove redundant words and make content more concise
* Prioritize natural and idiomatic phrasing, even if it means the text is slightly longer
* Avoid awkward or overly condensed constructions

{BREVITY_SPECIFIC_CONSTRAINTS}

{SHARED_CRITICAL_CONSTRAINTS}

Return only the edited version of the following wikitext:

{{wikitext}}
"""
        )

    @staticmethod
    def create_copyedit_prompt() -> PromptTemplate:
        """Creates a prompt template for general copy editing."""
        return PromptTemplate.from_template(
            f"""You are an expert editor specializing in clarity and correctness.

== Your Task ==

Perform a general copy edit on the following wikitext.

* Correct grammar, spelling, punctuation, and style
* Ensure clarity and coherence
* '''CAUTION WITH NUANCE AND COMPLEXITY:''' When rephrasing, especially for nuanced statements (relationships, sequences, causality, certainty, implications), TRIPLE-CHECK that your edits retain the EXACT original logical meaning and all subtleties. Prioritize precise meaning over style if subtleties are present.

{SHARED_CRITICAL_CONSTRAINTS}

Return only the edited version of the following wikitext:

{{wikitext}}
"""
        )

    @staticmethod
    def create_custom_prompt(
        task_description: str, specific_constraints: str = ""
    ) -> PromptTemplate:
        """Creates a custom prompt template with specified task and constraints."""
        constraints_section = (
            f"\n{specific_constraints}" if specific_constraints else ""
        )

        return PromptTemplate.from_template(
            f"""You are an expert editor.

== Your Task ==
{task_description}{constraints_section}

{SHARED_CRITICAL_CONSTRAINTS}

Return only the edited version of the following wikitext:

{{wikitext}}
"""
        )


class PromptManager:
    """Manages prompt templates and their associated configurations."""

    def __init__(self):
        self.templates = {
            "brevity": PromptTemplateFactory.create_brevity_prompt(),
            "copyedit": PromptTemplateFactory.create_copyedit_prompt(),
        }

    def get_template(self, mode: str) -> PromptTemplate:
        """Get a prompt template by mode name."""
        if mode not in self.templates:
            available_modes = list(self.templates.keys())
            raise ValueError(
                f"Unknown editing mode: {mode}. Available modes: {available_modes}"
            )
        return self.templates[mode]

    def add_custom_template(
        self, name: str, task_description: str, specific_constraints: str = ""
    ):
        """Add a custom prompt template."""
        self.templates[name] = PromptTemplateFactory.create_custom_prompt(
            task_description, specific_constraints
        )

    def list_available_modes(self) -> List[str]:
        """List all available editing modes."""
        return list(self.templates.keys())
