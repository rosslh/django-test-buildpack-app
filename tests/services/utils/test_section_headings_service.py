import os
from unittest.mock import patch

# Configure Django settings before importing Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")

import django
from django.conf import settings
from django.test import TestCase

if not settings.configured:
    django.setup()

from services.utils.section_headings_service import SectionHeadingsService
from services.utils.wikipedia_api import WikipediaAPIError


class TestSectionHeadingsService(TestCase):
    """Test SectionHeadingsService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = SectionHeadingsService()

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_success(self, mock_run_async, mock_extract_headings):
        """Test successful retrieval of section headings."""
        # Mock the async function call
        mock_run_async.return_value = (
            "== Overview ==\nContent\n== History ==\nMore content"
        )

        # Mock section headings extraction
        from collections import namedtuple

        SectionHeading = namedtuple("SectionHeading", ["text", "level"])
        mock_headings = [
            SectionHeading(text="Overview", level=2),
            SectionHeading(text="History", level=2),
        ]
        mock_extract_headings.return_value = mock_headings

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            return_value="https://en.wikipedia.org/wiki/Test_Article",
        ) as mock_get_url:
            result = self.service.get_section_headings("Test Article")

            # Verify the result
            self.assertEqual(result["article_title"], "Test Article")
            self.assertEqual(
                result["article_url"], "https://en.wikipedia.org/wiki/Test_Article"
            )
            self.assertEqual(len(result["headings"]), 2)
            self.assertEqual(result["headings"][0]["text"], "Overview")
            self.assertEqual(result["headings"][0]["level"], 2)
            self.assertEqual(result["headings"][1]["text"], "History")
            self.assertEqual(result["headings"][1]["level"], 2)

            # Verify mocks were called correctly
            mock_run_async.assert_called_once()
            mock_extract_headings.assert_called_once_with(
                "== Overview ==\nContent\n== History ==\nMore content"
            )
            mock_get_url.assert_called_once_with("Test Article")

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_no_headings(
        self, mock_run_async, mock_extract_headings
    ):
        """Test retrieval when no section headings are found."""
        # Mock the async function call
        mock_run_async.return_value = "No headings in this content"

        # Mock section headings extraction - no headings
        mock_extract_headings.return_value = []

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            return_value="https://en.wikipedia.org/wiki/Test_Article",
        ):
            result = self.service.get_section_headings("Test Article")

            # Verify the result
            self.assertEqual(result["article_title"], "Test Article")
            self.assertEqual(
                result["article_url"], "https://en.wikipedia.org/wiki/Test_Article"
            )
            self.assertEqual(len(result["headings"]), 0)

    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_wikipedia_api_error(self, mock_run_async):
        """Test handling of Wikipedia API errors."""
        # Mock the async function call to raise an error
        mock_run_async.side_effect = WikipediaAPIError("Article not found")

        with self.assertRaises(WikipediaAPIError) as cm:
            self.service.get_section_headings("NonExistentArticle")

        self.assertIn("Article not found", str(cm.exception))

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_extraction_error(
        self, mock_run_async, mock_extract_headings
    ):
        """Test handling of section headings extraction errors."""
        # Mock the async function call
        mock_run_async.return_value = "== Overview ==\nContent"

        # Mock section headings extraction to raise an error
        mock_extract_headings.side_effect = Exception("Extraction failed")

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            return_value="https://en.wikipedia.org/wiki/Test_Article",
        ):
            with self.assertRaises(Exception) as cm:
                self.service.get_section_headings("Test Article")

            self.assertIn("Extraction failed", str(cm.exception))

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_url_error(
        self, mock_run_async, mock_extract_headings
    ):
        """Test handling of URL generation errors."""
        # Mock the async function call
        mock_run_async.return_value = "== Overview ==\nContent"

        # Mock section headings extraction
        from collections import namedtuple

        SectionHeading = namedtuple("SectionHeading", ["text", "level"])
        mock_headings = [SectionHeading(text="Overview", level=2)]
        mock_extract_headings.return_value = mock_headings

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            side_effect=Exception("URL generation failed"),
        ):
            with self.assertRaises(Exception) as cm:
                self.service.get_section_headings("Test Article")

            self.assertIn("URL generation failed", str(cm.exception))

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_complex_headings(
        self, mock_run_async, mock_extract_headings
    ):
        """Test handling of complex section headings with different levels."""
        # Mock the async function call
        mock_run_async.return_value = "== Overview ==\nContent\n=== Subsection ===\nMore content\n== History ==\nContent"

        # Mock section headings extraction
        from collections import namedtuple

        SectionHeading = namedtuple("SectionHeading", ["text", "level"])
        mock_headings = [
            SectionHeading(text="Overview", level=2),
            SectionHeading(text="Subsection", level=3),
            SectionHeading(text="History", level=2),
        ]
        mock_extract_headings.return_value = mock_headings

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            return_value="https://en.wikipedia.org/wiki/Test_Article",
        ):
            result = self.service.get_section_headings("Test Article")

            # Verify the result
            self.assertEqual(len(result["headings"]), 3)
            self.assertEqual(result["headings"][0]["text"], "Overview")
            self.assertEqual(result["headings"][0]["level"], 2)
            self.assertEqual(result["headings"][1]["text"], "Subsection")
            self.assertEqual(result["headings"][1]["level"], 3)
            self.assertEqual(result["headings"][2]["text"], "History")
            self.assertEqual(result["headings"][2]["level"], 2)

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_empty_content(
        self, mock_run_async, mock_extract_headings
    ):
        """Test handling of empty content."""
        # Mock the async function call
        mock_run_async.return_value = ""

        # Mock section headings extraction
        mock_extract_headings.return_value = []

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            return_value="https://en.wikipedia.org/wiki/Test_Article",
        ):
            result = self.service.get_section_headings("Test Article")

            # Verify the result
            self.assertEqual(result["article_title"], "Test Article")
            self.assertEqual(
                result["article_url"], "https://en.wikipedia.org/wiki/Test_Article"
            )
            self.assertEqual(len(result["headings"]), 0)

    def test_service_initialization(self):
        """Test that the service initializes correctly."""
        service = SectionHeadingsService()
        self.assertIsNotNone(service.wikipedia_api)
        self.assertIsInstance(service.wikipedia_api, type(self.service.wikipedia_api))

    @patch("services.utils.section_headings_service.extract_section_headings")
    @patch("services.utils.section_headings_service._run_async_safely")
    def test_get_section_headings_with_special_characters(
        self, mock_run_async, mock_extract_headings
    ):
        """Test handling of article titles with special characters."""
        # Mock the async function call
        mock_run_async.return_value = "== Overview ==\nContent"

        # Mock section headings extraction
        from collections import namedtuple

        SectionHeading = namedtuple("SectionHeading", ["text", "level"])
        mock_headings = [SectionHeading(text="Overview", level=2)]
        mock_extract_headings.return_value = mock_headings

        with patch.object(
            self.service.wikipedia_api,
            "get_article_url",
            return_value="https://en.wikipedia.org/wiki/Test_Article_with_Spaces",
        ):
            result = self.service.get_section_headings("Test Article with Spaces")

            # Verify the result
            self.assertEqual(result["article_title"], "Test Article with Spaces")
            self.assertEqual(
                result["article_url"],
                "https://en.wikipedia.org/wiki/Test_Article_with_Spaces",
            )
            self.assertEqual(len(result["headings"]), 1)
