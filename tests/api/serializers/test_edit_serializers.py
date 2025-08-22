import os
from typing import Dict

import django
from django.conf import settings
from django.test import TestCase

# Configure Django settings before importing serializers
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")
    django.setup()

from api.serializers.edit_serializers import EditRequestSerializer


class TestEditRequestSerializer(TestCase):
    """Test EditRequestSerializer class."""

    def test_valid_article_and_section_title(self):
        """Test serializer with valid article and section title data."""
        data: Dict[str, str] = {"article_title": "Apollo", "section_title": "History"}
        serializer = EditRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["article_title"], "Apollo")
        self.assertEqual(serializer.validated_data["section_title"], "History")

    def test_missing_both_fields(self):
        """Test serializer with both fields missing."""
        data: Dict[str, str] = {}
        serializer = EditRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("article_title", serializer.errors)
        self.assertIn("section_title", serializer.errors)

    def test_empty_article_title(self):
        """Test serializer with empty article_title."""
        data: Dict[str, str] = {"article_title": "", "section_title": "History"}
        serializer = EditRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("article_title", serializer.errors)

    def test_only_section_title_provided(self):
        """Test serializer with only section_title provided without article_title."""
        data: Dict[str, str] = {"section_title": "History"}
        serializer = EditRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("article_title", serializer.errors)

    def test_article_title_with_whitespace(self):
        """Test serializer with article_title that has whitespace."""
        data: Dict[str, str] = {
            "article_title": "  Apollo Temple  ",
            "section_title": "History",
        }
        serializer = EditRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        # DRF CharField automatically strips whitespace by default
        self.assertEqual(serializer.validated_data["article_title"], "Apollo Temple")
        self.assertEqual(serializer.validated_data["section_title"], "History")

    def test_long_article_title(self):
        """Test serializer with very long article_title."""
        long_title = "A" * 200  # Within the 255 character limit
        data: Dict[str, str] = {"article_title": long_title, "section_title": "History"}
        serializer = EditRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["article_title"], long_title)
        self.assertEqual(serializer.validated_data["section_title"], "History")

    def test_article_title_too_long(self):
        """Test serializer with article_title exceeding max length."""
        long_title = "A" * 300  # Exceeds the 255 character limit
        data: Dict[str, str] = {"article_title": long_title}
        serializer = EditRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("article_title", serializer.errors)
