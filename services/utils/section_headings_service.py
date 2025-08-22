from typing import Any, Dict

from services.tasks.edit_tasks import _run_async_safely
from services.utils.wiki_utils import extract_section_headings
from services.utils.wikipedia_api import WikipediaAPI


class SectionHeadingsService:
    """Service for handling Wikipedia section headings extraction and processing."""

    def __init__(self):
        self.wikipedia_api = WikipediaAPI()

    def get_section_headings(self, article_title: str) -> Dict[str, Any]:
        """Retrieve level 2 section headings from a Wikipedia article.

        Args:
            article_title: The title of the Wikipedia article

        Returns:
            Dict containing headings data, article title, and article URL

        Raises:
            WikipediaAPIError: If there's an error fetching the article
        """
        # Fetch the article content using safe async handling
        wikitext = _run_async_safely(
            self.wikipedia_api.get_article_wikitext(article_title)
        )

        # Extract section headings from the wikitext
        section_headings = extract_section_headings(wikitext)

        # Convert SectionHeading namedtuples to dictionaries
        headings_data = [
            {"text": heading.text, "level": heading.level}
            for heading in section_headings
        ]

        # Get article URL
        article_url = self.wikipedia_api.get_article_url(article_title)

        response_data = {
            "headings": headings_data,
            "article_title": article_title,
            "article_url": article_url,
        }

        return response_data
