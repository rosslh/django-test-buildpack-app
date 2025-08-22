"""Validator for handling wikilinks."""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import wikitextparser as wtp

from services.core.interfaces import IReferenceHandler
from services.validation.base_validator import BaseValidator


@dataclass
class LinkInfo:
    target: str
    display_text: str
    full_wikitext: str
    link_type: str  # 'wikilink' or 'external'


class WikiLinkValidator(BaseValidator):
    """Handles validation and restoration of wikilinks."""

    def __init__(self, reference_handler: IReferenceHandler):
        self.reference_handler = reference_handler

    def _extract_links(self, text: str) -> List[LinkInfo]:
        """Extract all links (wikilinks and external) from the text, including trailing chars and pipe tricks."""
        parsed = wtp.parse(text)
        links: List[LinkInfo] = []

        # Handle wikilinks
        for link in parsed.wikilinks:
            link_str = str(link)
            # Find the position of this specific link instance in the text
            link_start = text.find(link_str)
            if link_start != -1:
                # Check for trailing characters after the link
                link_end = link_start + len(link_str)
                trailing = ""
                if link_end < len(text):
                    # Look for trailing word characters
                    match = re.match(r"(\w*)", text[link_end:])
                    if match:
                        trailing = match.group(1)

                # Use link.target for the target (handles section links correctly)
                # link.title is empty for section links, but link.target includes the #
                target = str(link.target) if link.target else str(link.title)

                if link.text is not None and str(link.text) != "":
                    display_text = str(link.text) + trailing
                    full_wikitext = link_str + trailing
                elif link.text is not None and str(link.text) == "":
                    # Pipe trick: use the part after the last opening parenthesis, or the whole title if no parentheses
                    title = target
                    if "(" in title:
                        display_text = title.split("(")[0].strip() + trailing
                    else:
                        display_text = title + trailing
                    # For pipe tricks, store the expanded form as full_wikitext
                    full_wikitext = (
                        f"[[{title}|{display_text.rstrip(trailing)}]]" + trailing
                    )
                else:
                    display_text = target + trailing
                    full_wikitext = link_str + trailing

                links.append(
                    LinkInfo(
                        target=target,
                        display_text=display_text,
                        full_wikitext=full_wikitext,
                        link_type="wikilink",
                    )
                )

        # Handle external links
        for link in parsed.external_links:
            link_str = str(link)
            display_text = str(link.text) if link.text else str(link.url)
            links.append(
                LinkInfo(
                    target=str(link.url),
                    display_text=display_text,
                    full_wikitext=link_str,
                    link_type="external",
                )
            )
        return links

    async def validate_and_reintroduce_links(
        self,
        original_paragraph_content: str,
        edited_text_with_placeholders: str,
        paragraph_index: int,
        total_paragraphs: int,
    ) -> Tuple[str, bool]:
        """Validates links in the edited text. Restores missing links using LinkInfo."""
        edited_text_with_placeholders = self._fix_malformed_pipe_links(
            edited_text_with_placeholders
        )

        original_with_placeholders, _ = (
            self.reference_handler.replace_references_with_placeholders(
                original_paragraph_content
            )
        )
        if not self._extract_links(original_with_placeholders):
            return self._handle_no_original_links(edited_text_with_placeholders)

        original_links = self._extract_links(original_with_placeholders)
        edited_links = self._extract_links(edited_text_with_placeholders)

        # 1. Link hijacking check
        hijack_result = self._check_link_hijacking(
            original_links, edited_links, original_paragraph_content
        )
        if hijack_result is not None:
            return hijack_result

        # 2. Duplicate link check
        duplicate_result = self._check_duplicate_links(
            original_links, edited_links, edited_text_with_placeholders
        )
        if duplicate_result is not None:
            return duplicate_result

        # 3. Remove newly added links
        working_text = self._remove_newly_added_links(
            original_links, edited_links, edited_text_with_placeholders
        )

        # 4. Restore missing links (new method)
        working_text, should_revert = self._restore_missing_links(
            original_links, working_text, original_paragraph_content
        )
        if should_revert:
            return original_paragraph_content, True

        # 5. Check for nested/invalid links after restoration
        if self._has_nested_links(working_text):
            return original_paragraph_content, True

        return working_text, False

    def _check_link_hijacking(
        self, original_links, edited_links, original_paragraph_content
    ):
        for original_link in original_links:
            for edited_link in edited_links:
                if (
                    original_link.display_text == edited_link.display_text
                    and original_link.target != edited_link.target
                    and original_link.link_type == edited_link.link_type
                ):
                    return original_paragraph_content, True
        return None

    def _check_duplicate_links(
        self, original_links, edited_links, edited_text_with_placeholders
    ):
        edited_link_targets = [
            link.target for link in edited_links if link.link_type == "wikilink"
        ]
        original_link_targets = [
            link.target for link in original_links if link.link_type == "wikilink"
        ]
        for target in set(original_link_targets):
            if edited_link_targets.count(target) > original_link_targets.count(target):
                return edited_text_with_placeholders, True
        return None

    def _remove_newly_added_links(
        self, original_links, edited_links, edited_text_with_placeholders
    ):
        # Changed: Only compare target and link_type, allow display text changes
        original_link_keys = {(link.target, link.link_type) for link in original_links}
        new_links = [
            link
            for link in edited_links
            if (link.target, link.link_type) not in original_link_keys
        ]
        working_text = edited_text_with_placeholders
        for link in new_links:
            result = self._attempt_link_removal(
                working_text, link.full_wikitext, link.target
            )
            working_text = result
        return working_text

    def _detect_display_text_updates(self, original_links, edited_links):
        """Detect links where only display text has changed."""
        updated_links = []
        for orig_link in original_links:
            for edited_link in edited_links:
                if (
                    orig_link.target == edited_link.target
                    and orig_link.link_type == edited_link.link_type
                    and orig_link.display_text != edited_link.display_text
                ):
                    updated_links.append((orig_link, edited_link))
        return updated_links

    def _restore_missing_links(
        self, original_links, working_text, original_paragraph_content
    ):
        edited_links = self._extract_links(working_text)
        # Changed: Only compare target and link_type, allow display text changes
        edited_link_keys = {(link.target, link.link_type) for link in edited_links}
        missing_links = [
            link
            for link in original_links
            if (link.target, link.link_type) not in edited_link_keys
        ]
        if not missing_links:
            return working_text, False

        # Find links with same target but different display text - these are display text updates
        self._detect_display_text_updates(original_links, edited_links)

        edited_links = self._extract_links(working_text)
        edited_link_keys = {(link.target, link.link_type) for link in edited_links}
        still_missing_links = [
            link
            for link in original_links
            if (link.target, link.link_type) not in edited_link_keys
        ]

        for link in still_missing_links:
            if self._attempt_single_link_restoration(link, working_text):
                working_text = self._get_updated_working_text(link, working_text)
                continue

            # 4. For external links, try alternative restoration strategies
            if link.link_type == "external":
                restored_text = self._attempt_external_link_restoration(
                    working_text, link
                )
                if restored_text is not None:
                    working_text = restored_text
                    continue
            return original_paragraph_content, True
        return working_text, False

    def _attempt_single_link_restoration(self, link, working_text):
        """Attempt various restoration strategies for a single missing link."""
        # Try different restoration strategies in order of preference
        strategies = [
            self._try_exact_word_boundary_match,
            self._try_case_insensitive_word_boundary_match,
            self._try_flexible_piped_link_restoration,
            self._try_trailing_chars_match,
            self._try_case_insensitive_trailing_chars_match,
            self._try_substring_replacement,
            self._try_case_insensitive_substring_replacement,
            self._try_flexible_target_substring_match,
        ]

        for strategy in strategies:
            if strategy(link, working_text):
                return True

        return False

    def _try_exact_word_boundary_match(self, link, working_text):
        """Try strict word-boundary replacement (exact case)."""
        pattern = r"\b" + re.escape(link.display_text) + r"\b"
        new_text, n = re.subn(pattern, link.full_wikitext, working_text, count=1)
        if n > 0:
            self._last_restoration_result = new_text
            return True
        return False

    def _try_case_insensitive_word_boundary_match(self, link, working_text):
        """Try case-insensitive word-boundary replacement."""
        pattern_case_insensitive = r"\b" + re.escape(link.display_text) + r"\b"
        new_text, n = re.subn(
            pattern_case_insensitive,
            link.full_wikitext,
            working_text,
            count=1,
            flags=re.IGNORECASE,
        )
        if n > 0:
            self._last_restoration_result = new_text
            return True
        return False

    def _try_flexible_piped_link_restoration(self, link, working_text):
        """Flexible display text matching: For piped links, try matching the target if display text doesn't match."""
        if not (
            link.link_type == "wikilink"
            and "|" in link.full_wikitext
            and link.target != link.display_text
        ):
            return False

        # For section links (starting with #), don't try to simplify them
        # They should preserve their original piped format
        if link.target.startswith("#"):
            return False

        # This is a regular piped link where display text differs from target
        # Try to match the target name instead of display text
        target_pattern = r"\b" + re.escape(link.target) + r"\b"
        simple_link = f"[[{link.target}]]"
        new_text, n = re.subn(target_pattern, simple_link, working_text, count=1)
        if n > 0:
            self._last_restoration_result = new_text
            return True

        # Try case-insensitive target matching
        new_text, n = re.subn(
            target_pattern, simple_link, working_text, count=1, flags=re.IGNORECASE
        )
        if n > 0:
            self._last_restoration_result = new_text
            return True

        return False

    def _try_trailing_chars_match(self, link, working_text):
        """Try matching display text with trailing characters (e.g., apples for [[apple]])."""
        trailing_pattern = re.compile(rf"({re.escape(link.display_text)})(\w*)")

        def trailing_repl(m, link=link):
            # Only replace if the match is not already a link
            return link.full_wikitext + m.group(2)

        new_text, n = trailing_pattern.subn(trailing_repl, working_text, count=1)
        if n > 0:
            self._last_restoration_result = new_text
            return True
        return False

    def _try_case_insensitive_trailing_chars_match(self, link, working_text):
        """Try case-insensitive matching with trailing characters."""
        trailing_pattern_ci = re.compile(
            rf"({re.escape(link.display_text)})(\w*)", re.IGNORECASE
        )

        def trailing_repl_ci(m, link=link):
            # Only replace if the match is not already a link
            return link.full_wikitext + m.group(2)

        new_text, n = trailing_pattern_ci.subn(trailing_repl_ci, working_text, count=1)
        if n > 0:
            self._last_restoration_result = new_text
            return True
        return False

    def _try_substring_replacement(self, link, working_text):
        """Try simple substring replacement (less strict)."""
        if link.display_text in working_text:
            new_text = working_text.replace(link.display_text, link.full_wikitext, 1)
            self._last_restoration_result = new_text
            return True
        return False

    def _try_case_insensitive_substring_replacement(self, link, working_text):
        """Try case-insensitive substring search and replace."""
        # Find case-insensitive match and replace with exact case preservation
        pattern_find = re.compile(re.escape(link.display_text), re.IGNORECASE)
        match = pattern_find.search(working_text)
        if match:
            new_text = (
                working_text[: match.start()]
                + link.full_wikitext
                + working_text[match.end() :]
            )
            self._last_restoration_result = new_text
            return True
        return False

    def _try_flexible_target_substring_match(self, link, working_text):
        """Flexible target matching for piped links (substring version)."""
        if not (
            link.link_type == "wikilink"
            and "|" in link.full_wikitext
            and link.target != link.display_text
        ):
            return False

        # For section links (starting with #), don't try to simplify them
        # They should preserve their original piped format
        if link.target.startswith("#"):
            return False

        # Try substring matching with the target
        if link.target in working_text:
            simple_link = f"[[{link.target}]]"
            new_text = working_text.replace(link.target, simple_link, 1)
            self._last_restoration_result = new_text
            return True

        # Try case-insensitive target substring matching
        pattern_find = re.compile(re.escape(link.target), re.IGNORECASE)
        match = pattern_find.search(working_text)
        if match:
            simple_link = f"[[{link.target}]]"
            new_text = (
                working_text[: match.start()]
                + simple_link
                + working_text[match.end() :]
            )
            self._last_restoration_result = new_text
            return True

        return False

    def _get_updated_working_text(self, link, working_text):
        """Get the updated working text after successful link restoration."""
        return getattr(self, "_last_restoration_result", working_text)

    def _handle_no_original_links(self, edited_text: str) -> Tuple[str, bool]:
        """Remove all links from the edited text, replacing them with their display text."""
        links = self._extract_links(edited_text)
        working_text = edited_text
        for link in links:
            # Use _attempt_link_removal for proper removal logic
            working_text = self._attempt_link_removal(
                working_text, link.full_wikitext, link.target
            )
        return working_text, False

    def _attempt_link_removal(
        self, edited_text: str, full_link: str, target: str
    ) -> str:
        """Attempt to remove a wikilink while preserving its display text.

        This is used when the LLM adds a link that wasn't in the original text.
        Returns the modified text with the link replaced by its display text.
        """
        display_text = self._extract_display_text_from_link(full_link, target)

        # Replace the link with its display text
        # Use count=1 to only replace the first occurrence, to be safe
        new_text = edited_text.replace(full_link, display_text, 1)
        return new_text

    def _extract_display_text_from_link(self, full_link: str, target: str) -> str:
        """Extract display text from a full wikilink string.

        Example: [[Target|Display Text]] -> "Display Text"
        Example: [[Target]] -> "Target"
        """
        try:
            parsed_link = wtp.parse(full_link).wikilinks[0]
            if parsed_link.text:
                return str(parsed_link.text)
            return target
        except (IndexError, AttributeError):
            # If parsing fails or no wikilinks found, return the target
            return target

    def _attempt_external_link_restoration(
        self, edited_text: str, link: LinkInfo
    ) -> Optional[str]:
        """Attempt to restore an external link that was completely removed."""
        # For simple external links where display_text == URL, try to find where to insert the link
        if link.display_text == link.target:
            # Look for patterns that suggest where the link was removed
            # For example, "An example: ." might have had a link before the period

            # Try to find a position where we can reasonably restore the link
            # Look for patterns like ": ." or " ." that might indicate removed content
            patterns_to_try = [
                # Pattern: ": ." -> ": [link]."
                (r":\s*\.", f": {link.full_wikitext}."),
                # Pattern: " ." -> " [link]."
                (r"\s+\.", f" {link.full_wikitext}."),
                # Pattern: end of sentence followed by space and punctuation
                (r"\s*\.$", f" {link.full_wikitext}."),
            ]

            for pattern, replacement in patterns_to_try:
                if re.search(pattern, edited_text):
                    new_text = re.sub(pattern, replacement, edited_text, count=1)
                    if new_text != edited_text:
                        return new_text

        # If display text is different from URL, try to find the display text
        elif link.display_text in edited_text:
            # Replace display text with full link
            new_text = edited_text.replace(link.display_text, link.full_wikitext, 1)
            return new_text

        # If we can't find a good restoration strategy, return None
        return None

    def _has_nested_links(self, text: str) -> bool:
        """Check if the text contains nested or invalid wikilink patterns.

        Detects patterns like:
        - [[[[link]] rest]] (nested opening brackets)
        - [[link [[other]]]] (link within link)
        - Other malformed link structures
        """
        import re

        # Pattern 1: Multiple consecutive opening brackets (e.g., [[[[)
        if re.search(r"\[\[\[\[", text):
            return True

        # Pattern 2: Multiple consecutive closing brackets (e.g., ]]]])
        if re.search(r"\]\]\]\]", text):
            return True

        # Pattern 3: Link opening brackets inside another link
        # This is more complex - we need to track bracket nesting
        bracket_depth = 0
        i = 0
        while i < len(text) - 1:
            if text[i : i + 2] == "[[":
                bracket_depth += 1
                if bracket_depth > 1:
                    return True
                i += 2
            elif text[i : i + 2] == "]]":
                bracket_depth -= 1
                i += 2
            else:
                i += 1

        return False

    def _fix_malformed_pipe_links(self, text: str) -> str:
        """Fix malformed pipe links like [[Target|]] with empty display text.

        Converts malformed pipe links (where display text is empty) to simple links.
        Example: [[Target|]] becomes [[Target]]

        This is a common LLM error where the model creates incomplete pipe syntax.
        """
        import wikitextparser as wtp

        parsed = wtp.parse(text)

        for link in parsed.wikilinks:
            # Check if this is a malformed pipe link (has pipe but empty display text)
            if link.text is not None and str(link.text).strip() == "":
                # Convert [[Target|]] to [[Target]]
                old_link = str(link)
                new_link = f"[[{link.title}]]"
                text = text.replace(old_link, new_link, 1)

        return text
