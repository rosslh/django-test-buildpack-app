"""Wikipedia API client for fetching article content.

This module provides functionality to fetch Wikipedia article content using the MediaWiki API.
"""

from typing import Any, Dict

import httpx


class WikipediaAPIError(Exception):
    """Exception raised when Wikipedia API requests fail."""

    pass


class WikipediaAPI:
    """Client for fetching Wikipedia article content via MediaWiki API."""

    def __init__(self, language: str = "en", timeout: int = 30):
        """Initialize the Wikipedia API client.

        Args:
            language: Wikipedia language code (default: "en")
            timeout: Request timeout in seconds (default: 30)
        """
        self.language = language
        self.timeout = timeout
        self.base_url = f"https://{language}.wikipedia.org/w/api.php"

    async def get_article_wikitext(self, title: str) -> str:
        """Fetch the wikitext content of a Wikipedia article.

        Args:
            title: The title of the Wikipedia article

        Returns:
            The wikitext content of the article

        Raises:
            WikipediaAPIError: If the article cannot be fetched or doesn't exist
        """
        self._validate_title(title)
        title = title.strip()
        normalized_title = await self._normalize_title_with_error_handling(title)
        params = self._get_query_params(normalized_title)
        data = await self._fetch_article_data(params, title)
        content = self._extract_content_from_data(data, title)
        return content

    def _validate_title(self, title: str):
        if not title or not title.strip():
            raise WikipediaAPIError("Article title cannot be empty")

    async def _normalize_title_with_error_handling(self, title: str) -> str:
        normalized_title = await self._normalize_title(title)
        return normalized_title

    def _get_query_params(self, normalized_title: str) -> Dict[str, Any]:
        return {
            "action": "query",
            "format": "json",
            "titles": normalized_title,
            "prop": "revisions",
            "rvprop": "content",
            "rvlimit": 1,
            "formatversion": 2,
        }

    async def _fetch_article_data(
        self, params: Dict[str, Any], title: str
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    error_info = data["error"]["info"]
                    raise WikipediaAPIError(f"Wikipedia API error: {error_info}")
                return data
        except httpx.HTTPError as e:
            raise WikipediaAPIError(f"HTTP error while fetching article: {e}") from e
        except Exception as e:
            if isinstance(e, WikipediaAPIError):
                raise
            raise WikipediaAPIError(
                f"Unexpected error while fetching article: {e}"
            ) from e

    def _extract_content_from_data(self, data: Dict[str, Any], title: str) -> str:
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            raise WikipediaAPIError(f"No pages found for title: {title}")
        page = pages[0]
        if "missing" in page:
            raise WikipediaAPIError(f"Article not found: {title}")
        revisions = page.get("revisions", [])
        if not revisions:
            raise WikipediaAPIError(f"No content found for article: {title}")
        content = revisions[0].get("content", "")
        if not content:
            raise WikipediaAPIError(f"Empty content for article: {title}")
        return content

    async def _normalize_title(self, title: str) -> str:
        """Normalize a Wikipedia article title and handle redirects.

        Args:
            title: The original article title

        Returns:
            The normalized title after following redirects
        """
        params: Dict[str, Any] = {
            "action": "query",
            "format": "json",
            "titles": title,
            "redirects": 1,
            "formatversion": 2,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                data = response.json()

                if "error" in data:
                    # If there's an error in normalization, return the original title
                    return title

                # Check if there were redirects
                redirects = data.get("query", {}).get("redirects", [])
                if redirects:
                    return redirects[-1].get("to", title)

                # Check if the title was normalized
                normalized = data.get("query", {}).get("normalized", [])
                if normalized:
                    return normalized[0].get("to", title)

                return title

        except Exception:
            # If normalization fails, return the original title
            return title

    def get_article_url(self, title: str) -> str:
        """Get the URL for a Wikipedia article.

        Args:
            title: The article title

        Returns:
            The URL to the Wikipedia article
        """
        encoded_title = title.replace(" ", "_")
        return f"https://{self.language}.wikipedia.org/wiki/{encoded_title}"
