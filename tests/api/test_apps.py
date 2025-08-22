"""Tests for API app configuration."""

from django.apps import apps
from django.test import TestCase

from api.apps import ApiConfig


class TestApiConfig(TestCase):
    """Test API app configuration."""

    def test_app_config(self):
        """Test that the app config is properly configured."""
        app_config = apps.get_app_config("api")
        self.assertIsInstance(app_config, ApiConfig)
        self.assertEqual(app_config.name, "api")
        self.assertEqual(app_config.verbose_name, "API Layer")
