"""Factory classes for creating various components with dependency injection.

This module provides factory methods for creating instances of different components,
allowing for easy testing and configuration.
"""

from typing import Any, Dict, cast

from services.core.interfaces import (
    IReferenceHandler,
    IReversionTracker,
)


class ValidatorFactory:
    """Factory for creating validator instances."""

    @staticmethod
    def create_wikilink_validator() -> Any:
        """Create a WikiLink validator with singleton reference handler."""
        from services.validation.validators.wiki_link_validator import WikiLinkValidator

        reference_handler = ProcessorFactory.create_reference_handler()
        return WikiLinkValidator(reference_handler)

    @staticmethod
    def create_reference_validator() -> Any:
        """Create a Reference validator."""
        from services.validation.validators.reference_validator import (
            ReferenceValidator,
        )

        return ReferenceValidator()

    @staticmethod
    def create_spelling_validator() -> Any:
        """Create a Spelling validator."""
        from services.validation.validators.spelling_validator import SpellingValidator

        return SpellingValidator()

    @staticmethod
    def create_list_marker_validator() -> Any:
        """Create a List Marker validator."""
        from services.validation.validators.list_marker_validator import (
            ListMarkerValidator,
        )

        return ListMarkerValidator()

    @staticmethod
    def create_template_validator() -> Any:
        """Create a Template validator."""
        from services.validation.validators.template_validator import TemplateValidator

        return TemplateValidator()

    @staticmethod
    def create_quote_validator() -> Any:
        """Create a Quote validator."""
        from services.validation.validators.quote_validator import QuoteValidator

        return QuoteValidator()

    @staticmethod
    def create_meta_commentary_validator() -> Any:
        """Create a Meta Commentary validator."""
        from services.validation.validators.meta_commentary_validator import (
            MetaCommentaryValidator,
        )

        return MetaCommentaryValidator()

    @staticmethod
    def create_all_validators() -> Dict[str, Any]:
        """Create all validators and return them in a dictionary."""
        return {
            "link_validator": ValidatorFactory.create_wikilink_validator(),
            "reference_validator": ValidatorFactory.create_reference_validator(),
            "spelling_validator": ValidatorFactory.create_spelling_validator(),
            "list_marker_validator": ValidatorFactory.create_list_marker_validator(),
            "template_validator": ValidatorFactory.create_template_validator(),
            "quote_validator": ValidatorFactory.create_quote_validator(),
            "meta_commentary_validator": ValidatorFactory.create_meta_commentary_validator(),
        }


class TrackerFactory:
    """Factory for creating tracker instances."""

    @staticmethod
    def create_reversion_tracker() -> IReversionTracker:
        """Create a reversion tracker."""
        from services.tracking.reversion_tracker import ReversionTracker

        return cast(IReversionTracker, ReversionTracker())


class ProcessorFactory:
    """Factory for creating processor instances."""

    _reference_handler_instance = None

    @staticmethod
    def create_document_parser() -> Any:
        """Create a document parser."""
        from services.document.parser import DocumentParser

        return DocumentParser()

    @staticmethod
    def create_reference_handler() -> IReferenceHandler:
        """Create or return the singleton reference handler instance."""
        if ProcessorFactory._reference_handler_instance is None:
            from services.text.reference_handler import ReferenceHandler

            ProcessorFactory._reference_handler_instance = ReferenceHandler()
        return ProcessorFactory._reference_handler_instance
