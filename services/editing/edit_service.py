"""WikiEditor class for orchestrating the wiki editing process."""

from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser

from api.exceptions import ErrorSanitizer
from services.core.factories import (
    ProcessorFactory,
    TrackerFactory,
    ValidatorFactory,
)
from services.core.interfaces import (
    IContentClassifier,
    IDocumentProcessor,
    IReferenceHandler,
    IReversionTracker,
)
from services.document.classifier import ContentClassifier
from services.editing.edit_orchestrator import EditOrchestrator, ParagraphResult
from services.editing.paragraph_processor import ParagraphProcessor
from services.prompts.prompt_manager import PromptManager
from services.utils.wikipedia_api import WikipediaAPI, WikipediaAPIError
from services.validation.adapters import (
    AddedContentValidatorAdapter,
    CompositeReferenceValidatorAdapter,
    ListMarkerValidatorAdapter,
    MetaCommentaryValidatorAdapter,
    QuoteValidatorAdapter,
    ReferenceContentValidatorAdapter,
    SpellingValidatorAdapter,
    TemplateValidatorAdapter,
    WikiLinkValidatorAdapter,
)
from services.validation.pipeline import ValidationPipelineBuilder


class WikiEditor:
    """Orchestrates the wiki editing process using modular components.

    This class now uses dependency injection and delegates responsibilities to
    specialized components, following SOLID principles.
    """

    def __init__(
        self,
        llm,
        editing_mode: str,
        verbose: bool = False,
        document_processor: Optional[IDocumentProcessor] = None,
        content_classifier: Optional[IContentClassifier] = None,
        reversion_tracker: Optional[IReversionTracker] = None,
        reference_handler: Optional[IReferenceHandler] = None,
    ):
        """Initialize WikiEditor with dependency injection support."""
        self.llm = llm
        self.verbose = verbose
        self.editing_mode = editing_mode

        self.reversion_tracker = (
            reversion_tracker or TrackerFactory.create_reversion_tracker()
        )

        self.document_processor = (
            document_processor or ProcessorFactory.create_document_parser()
        )
        self.content_classifier = content_classifier or ContentClassifier()
        self.reference_handler = (
            reference_handler or ProcessorFactory.create_reference_handler()
        )

        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize all components with proper configuration."""
        validators = ValidatorFactory.create_all_validators()

        self.post_processing_pipeline = self._build_post_processing_pipeline(validators)
        self.pre_processing_pipeline = self._build_pre_processing_pipeline()

        prompt_manager = PromptManager()
        prompt_template = prompt_manager.get_template(self.editing_mode)
        self.chain = prompt_template | self.llm | StrOutputParser()

        self.paragraph_processor = ParagraphProcessor(
            llm_chain=self.chain,
            pre_processing_pipeline=self.pre_processing_pipeline,
            post_processing_pipeline=self.post_processing_pipeline,
            reversion_tracker=self.reversion_tracker,
            reference_handler=self.reference_handler,
        )

        self.orchestrator = EditOrchestrator(
            document_processor=self.document_processor,
            content_classifier=self.content_classifier,
            reversion_tracker=self.reversion_tracker,
            reference_handler=self.reference_handler,
        )

    def _build_pre_processing_pipeline(self) -> Any:
        """Build an empty pre-processing pipeline.

        Pre-processing (reference placeholder replacement) is handled directly
        in the orchestrator, so this returns an empty pipeline.
        """
        builder = ValidationPipelineBuilder()
        return builder.build()

    def _build_post_processing_pipeline(self, validators: Dict[str, Any]) -> Any:
        """Build the post-processing validation pipeline.

        Execution order is critical:
        1. Async content modifiers (remove newly added content)
        2. Sync content modifiers (fix formatting issues)
        3. Sync content validators (validate cleaned content)
        """
        builder = ValidationPipelineBuilder()

        # 1. ASYNC CONTENT MODIFIERS (run first)
        # Remove newly added wikilinks before other validators see them
        link_adapter = WikiLinkValidatorAdapter(validators["link_validator"])
        builder.add_async_validator(link_adapter)

        # 2. SYNC CONTENT MODIFIERS (run before validators)
        # Restore/fix templates before validation
        template_adapter = TemplateValidatorAdapter(
            validators["template_validator"], self.reference_handler
        )
        builder.add_validator(template_adapter)

        # Restore/fix quotes before validation
        quote_adapter = QuoteValidatorAdapter(
            validators["quote_validator"], self.reference_handler
        )
        builder.add_validator(quote_adapter)

        # Correct regional spelling before validation
        spelling_adapter = SpellingValidatorAdapter(validators["spelling_validator"])
        builder.add_validator(spelling_adapter)

        # Restore list markers before validation
        list_marker_adapter = ListMarkerValidatorAdapter(
            validators["list_marker_validator"]
        )
        builder.add_validator(list_marker_adapter)

        # 3. SYNC CONTENT VALIDATORS (run after content is cleaned)
        # Validate references are not removed
        ref_adapter = CompositeReferenceValidatorAdapter(
            validators["reference_validator"],
            self.reversion_tracker,
        )
        builder.add_validator(ref_adapter)

        # Validate reference content is not changed
        ref_content_adapter = ReferenceContentValidatorAdapter(
            validators["reference_validator"], self.reference_handler
        )
        builder.add_validator(ref_content_adapter)

        # Validate no new content was added (runs after cleanup)
        added_content_adapter = AddedContentValidatorAdapter(
            validators["reference_validator"], self.reference_handler
        )
        builder.add_validator(added_content_adapter)

        # Validate no meta commentary was added
        meta_commentary_adapter = MetaCommentaryValidatorAdapter(
            validators["meta_commentary_validator"]
        )
        builder.add_validator(meta_commentary_adapter)

        return builder.build()

    async def edit_wikitext_structured(
        self, text: str, enhanced_progress_callback=None
    ) -> List[ParagraphResult]:
        """Main entry point for editing wikitext and returning structured paragraph results.

        Args:
            text: The wikitext to edit
            enhanced_progress_callback: Optional callback for enhanced progress with granular phases

        Returns:
            List of ParagraphResult objects with before/after content and status
        """
        if not text.strip():
            return []

        try:
            paragraph_results = await self.orchestrator.orchestrate_edit_structured(
                text, self.paragraph_processor, enhanced_progress_callback
            )
        except Exception as e:
            # Return all paragraphs as unchanged
            try:
                document_items = self.document_processor.process(text)

                # Create safe error message using sanitizer
                sanitized_error = ErrorSanitizer.sanitize_exception(e)
                error_message = sanitized_error.user_message

                # Optimize memory usage for large documents by limiting error objects
                # For very large documents, return a single error result instead of one per item
                if len(document_items) > 100:
                    # Return a single error result representing the entire document
                    full_text = "\n".join(document_items)
                    return [
                        ParagraphResult(
                            before=full_text,
                            after=full_text,
                            status="ERRORED",
                            status_details=f"Processing failed for large document ({len(document_items)} items): {error_message}",
                        )
                    ]
                else:
                    # For smaller documents, maintain the original behavior
                    return [
                        ParagraphResult(
                            before=item,
                            after=item,
                            status="ERRORED",
                            status_details=error_message,
                        )
                        for item in document_items
                    ]
            except Exception as fallback_error:
                # Create safe error messages for the fallback scenario
                primary_error = ErrorSanitizer.sanitize_exception(e)
                fallback_error_sanitized = ErrorSanitizer.sanitize_exception(
                    fallback_error
                )
                combined_message = f"Critical processing failure - {primary_error.user_message}. Additionally, document parsing failed: {fallback_error_sanitized.user_message}"

                # Return a single unchanged result with the original text
                return [
                    ParagraphResult(
                        before=text,
                        after=text,
                        status="ERRORED",
                        status_details=combined_message,
                    )
                ]

        return paragraph_results

    async def edit_wikitext_structured_batched(
        self, text: str, enhanced_progress_callback=None, batch_size: int = 5
    ) -> List[ParagraphResult]:
        """Edit wikitext using batched paragraph processing to reduce overhead.

        Args:
            text: The wikitext to edit
            enhanced_progress_callback: Optional callback for enhanced progress with granular phases
            batch_size: Number of paragraphs to process per batch

        Returns:
            List of ParagraphResult objects with before/after content and status
        """
        if not text.strip():
            return []

        try:
            paragraph_results = await self.orchestrator.orchestrate_edit_structured_batched(
                text, self.paragraph_processor, enhanced_progress_callback, batch_size
            )
        except Exception as e:
            # Return all paragraphs as unchanged - same error handling as regular method
            try:
                document_items = self.document_processor.process(text)

                # Create safe error message using sanitizer
                sanitized_error = ErrorSanitizer.sanitize_exception(e)
                error_message = sanitized_error.user_message

                # Optimize memory usage for large documents by limiting error objects
                if len(document_items) > 100:
                    full_text = "\n".join(document_items)
                    return [
                        ParagraphResult(
                            before=full_text,
                            after=full_text,
                            status="ERRORED",
                            status_details=f"Batched processing failed for large document ({len(document_items)} items): {error_message}",
                        )
                    ]
                else:
                    return [
                        ParagraphResult(
                            before=item,
                            after=item,
                            status="ERRORED",
                            status_details=error_message,
                        )
                        for item in document_items
                    ]
            except Exception as fallback_error:
                primary_error = ErrorSanitizer.sanitize_exception(e)
                fallback_error_sanitized = ErrorSanitizer.sanitize_exception(
                    fallback_error
                )
                combined_message = f"Critical batched processing failure - {primary_error.user_message}. Additionally, document parsing failed: {fallback_error_sanitized.user_message}"

                return [
                    ParagraphResult(
                        before=text,
                        after=text,
                        status="ERRORED",
                        status_details=combined_message,
                    )
                ]

        return paragraph_results

    async def edit_article_by_title_structured(
        self, article_title: str, language: str = "en"
    ) -> List[ParagraphResult]:
        """Edit a Wikipedia article by its title and return structured paragraph results.

        This method fetches the article content from Wikipedia and then edits it.

        Args:
            article_title: The title of the Wikipedia article to edit
            language: Wikipedia language code (default: "en")

        Returns:
            List of ParagraphResult objects with before/after content and status

        Raises:
            WikipediaAPIError: If the article cannot be fetched
        """
        if not article_title or not article_title.strip():
            raise ValueError("Article title cannot be empty")

        # Initialize Wikipedia API client
        wikipedia_api = WikipediaAPI(language=language)

        try:
            # Fetch the article content
            wikitext = await wikipedia_api.get_article_wikitext(article_title)

            # Edit the content using the structured edit method
            paragraph_results = await self.edit_wikitext_structured(wikitext)

            return paragraph_results

        except WikipediaAPIError:
            raise

    async def edit_article_section_structured(
        self,
        article_title: str,
        section_title: str,
        language: str = "en",
        enhanced_progress_callback=None,
    ) -> List[ParagraphResult]:
        """Edit a specific section of a Wikipedia article by its title and return structured paragraph results.

        This method fetches the article content from Wikipedia, extracts the specified section, and then edits it.

        Args:
            article_title: The title of the Wikipedia article
            section_title: The title of the section to edit within the article
            language: Wikipedia language code (default: "en")
            enhanced_progress_callback: Optional callback for enhanced progress with granular phases

        Returns:
            List of ParagraphResult objects with before/after content and status

        Raises:
            WikipediaAPIError: If the article cannot be fetched
            ValueError: If the section cannot be found
        """
        if not article_title or not article_title.strip():
            raise ValueError("Article title cannot be empty")

        if not section_title or not section_title.strip():
            raise ValueError("Section title cannot be empty")

        # Initialize Wikipedia API client
        wikipedia_api = WikipediaAPI(language=language)

        # Fetch the article content
        wikitext = await wikipedia_api.get_article_wikitext(article_title)

        # Extract the specific section content
        from services.utils.wiki_utils import extract_section_content

        section_content = extract_section_content(wikitext, section_title)

        if section_content is None:
            raise ValueError(
                f"Section '{section_title}' not found in article '{article_title}'"
            )

        # Edit the section content using the structured edit method
        paragraph_results = await self.edit_wikitext_structured(
            section_content, enhanced_progress_callback
        )

        return paragraph_results

    async def edit_article_section_structured_batched(
        self,
        article_title: str,
        section_title: str,
        language: str = "en",
        enhanced_progress_callback=None,
        batch_size: int = 5,
    ) -> List[ParagraphResult]:
        """Edit a specific section of a Wikipedia article with batched paragraph processing.

        This method fetches the article content from Wikipedia, extracts the specified section,
        and then edits it using batched processing to reduce task overhead.

        Args:
            article_title: The title of the Wikipedia article
            section_title: The title of the section to edit within the article
            language: Wikipedia language code (default: "en")
            enhanced_progress_callback: Optional callback for enhanced progress with granular phases
            batch_size: Number of paragraphs to process per batch

        Returns:
            List of ParagraphResult objects with before/after content and status

        Raises:
            WikipediaAPIError: If the article cannot be fetched
            ValueError: If the section cannot be found
        """
        if not article_title or not article_title.strip():
            raise ValueError("Article title cannot be empty")

        if not section_title or not section_title.strip():
            raise ValueError("Section title cannot be empty")

        # Initialize Wikipedia API client
        wikipedia_api = WikipediaAPI(language=language)

        # Fetch the article content
        wikitext = await wikipedia_api.get_article_wikitext(article_title)

        # Extract the specific section content
        from services.utils.wiki_utils import extract_section_content

        section_content = extract_section_content(wikitext, section_title)

        if section_content is None:
            raise ValueError(
                f"Section '{section_title}' not found in article '{article_title}'"
            )

        # Edit the section content using the batched structured edit method
        paragraph_results = await self.edit_wikitext_structured_batched(
            section_content, enhanced_progress_callback, batch_size
        )

        return paragraph_results
