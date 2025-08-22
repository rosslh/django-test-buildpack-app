"""Tests for Wikipedia API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.utils.wikipedia_api import WikipediaAPI, WikipediaAPIError


class TestWikipediaAPI:
    """Test cases for WikipediaAPI class."""

    @pytest.fixture
    def wikipedia_api(self):
        """Create a WikipediaAPI instance for testing."""
        return WikipediaAPI()

    def test_initialization(self, wikipedia_api):
        """Test WikipediaAPI initialization."""
        assert wikipedia_api.language == "en"
        assert wikipedia_api.timeout == 30
        assert wikipedia_api.base_url == "https://en.wikipedia.org/w/api.php"

    def test_initialization_with_custom_language(self):
        """Test WikipediaAPI initialization with custom language."""
        api = WikipediaAPI(language="fr", timeout=60)
        assert api.language == "fr"
        assert api.timeout == 60
        assert api.base_url == "https://fr.wikipedia.org/w/api.php"

    def test_get_article_url(self, wikipedia_api):
        """Test get_article_url method."""
        url = wikipedia_api.get_article_url("Apollo")
        assert url == "https://en.wikipedia.org/wiki/Apollo"

    def test_get_article_url_with_spaces(self, wikipedia_api):
        """Test get_article_url method with spaces in title."""
        url = wikipedia_api.get_article_url("Python programming language")
        assert url == "https://en.wikipedia.org/wiki/Python_programming_language"

    @pytest.mark.asyncio
    async def test_get_article_wikitext_empty_title(self, wikipedia_api):
        """Test get_article_wikitext with empty title."""
        with pytest.raises(WikipediaAPIError, match="Article title cannot be empty"):
            await wikipedia_api.get_article_wikitext("")

        with pytest.raises(WikipediaAPIError, match="Article title cannot be empty"):
            await wikipedia_api.get_article_wikitext("   ")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_get_article_wikitext_success(self, mock_client, wikipedia_api):
        """Test successful article fetching."""
        # Mock the normalize title response
        normalize_response = MagicMock()
        normalize_response.json.return_value = {
            "query": {"normalized": [{"from": "apollo", "to": "Apollo"}]}
        }

        # Mock the article content response
        content_response = MagicMock()
        content_response.json.return_value = {
            "query": {
                "pages": [
                    {
                        "title": "Apollo",
                        "revisions": [{"content": "Apollo is a Greek god..."}],
                    }
                ]
            }
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await wikipedia_api.get_article_wikitext("apollo")
        assert result == "Apollo is a Greek god..."

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_get_article_wikitext_article_not_found(
        self, mock_client, wikipedia_api
    ):
        """Test article not found error."""
        # Mock the normalize title response
        normalize_response = MagicMock()
        normalize_response.json.return_value = {"query": {}}

        # Mock the article content response for missing article
        content_response = MagicMock()
        content_response.json.return_value = {
            "query": {"pages": [{"title": "NonExistentArticle", "missing": True}]}
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(
            WikipediaAPIError, match="Article not found: NonExistentArticle"
        ):
            await wikipedia_api.get_article_wikitext("NonExistentArticle")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_get_article_wikitext_api_error(self, mock_client, wikipedia_api):
        """Test Wikipedia API error handling."""
        # Mock the normalize title response
        normalize_response = MagicMock()
        normalize_response.json.return_value = {"query": {}}

        # Mock the article content response with API error
        content_response = MagicMock()
        content_response.json.return_value = {
            "error": {"info": "Service temporarily unavailable"}
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(
            WikipediaAPIError,
            match="Wikipedia API error: Service temporarily unavailable",
        ):
            await wikipedia_api.get_article_wikitext("Apollo")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_get_article_wikitext_no_revisions(self, mock_client, wikipedia_api):
        """Test article with no revisions error."""
        # Mock the normalize title response
        normalize_response = MagicMock()
        normalize_response.json.return_value = {"query": {}}

        # Mock the article content response with no revisions
        content_response = MagicMock()
        content_response.json.return_value = {
            "query": {"pages": [{"title": "Apollo", "revisions": []}]}
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(
            WikipediaAPIError, match="No content found for article: Apollo"
        ):
            await wikipedia_api.get_article_wikitext("Apollo")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_get_article_wikitext_empty_content(self, mock_client, wikipedia_api):
        """Test article with empty content error."""
        # Mock the normalize title response
        normalize_response = MagicMock()
        normalize_response.json.return_value = {"query": {}}

        # Mock the article content response with empty content
        content_response = MagicMock()
        content_response.json.return_value = {
            "query": {"pages": [{"title": "Apollo", "revisions": [{"content": ""}]}]}
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(
            WikipediaAPIError, match="Empty content for article: Apollo"
        ):
            await wikipedia_api.get_article_wikitext("Apollo")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_normalize_title_with_redirect(self, mock_client, wikipedia_api):
        """Test title normalization with redirect."""
        # Mock the normalize title response with redirect
        normalize_response = MagicMock()
        normalize_response.json.return_value = {
            "query": {
                "redirects": [
                    {"from": "apollo", "to": "Apollo (disambiguation)"},
                    {"from": "Apollo (disambiguation)", "to": "Apollo"},
                ]
            }
        }

        # Mock the article content response
        content_response = MagicMock()
        content_response.json.return_value = {
            "query": {
                "pages": [
                    {
                        "title": "Apollo",
                        "revisions": [{"content": "Apollo is a Greek god..."}],
                    }
                ]
            }
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await wikipedia_api.get_article_wikitext("apollo")
        assert result == "Apollo is a Greek god..."

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_http_error_handling(self, mock_client, wikipedia_api):
        """Test HTTP error handling."""
        import httpx

        # Configure the mock client to raise HTTP error
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.HTTPError("Connection failed")
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(
            WikipediaAPIError,
            match="HTTP error while fetching article: Connection failed",
        ):
            await wikipedia_api.get_article_wikitext("Apollo")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_unexpected_error_handling(self, mock_client, wikipedia_api):
        """Test unexpected error handling."""
        # Configure the mock client to raise unexpected error
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = ValueError("Unexpected error")
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(
            WikipediaAPIError,
            match="Unexpected error while fetching article: Unexpected error",
        ):
            await wikipedia_api.get_article_wikitext("Apollo")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_get_article_wikitext_no_pages(self, mock_client, wikipedia_api):
        """Test no pages found error."""
        # Mock the normalize title response
        normalize_response = MagicMock()
        normalize_response.json.return_value = {"query": {}}

        # Mock the article content response with no pages
        content_response = MagicMock()
        content_response.json.return_value = {"query": {"pages": []}}

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [normalize_response, content_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(WikipediaAPIError, match="No pages found for title: Apollo"):
            await wikipedia_api.get_article_wikitext("Apollo")

    @pytest.mark.asyncio
    @patch("services.utils.wikipedia_api.httpx.AsyncClient")
    async def test_normalize_title_with_error(self, mock_client, wikipedia_api):
        """Test title normalization with API error."""
        # Mock the normalize title response with error
        normalize_response = MagicMock()
        normalize_response.json.return_value = {
            "error": {"code": "invalidtitle", "info": "Bad title"}
        }

        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = normalize_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Test that the original title is returned when there's an error
        result = await wikipedia_api._normalize_title("bad*title")
        assert result == "bad*title"
