"""Tests for Data app configuration."""

from django.apps import apps
from django.test import TestCase

from data.apps import DataConfig


class TestDataConfig(TestCase):
    """Test Data app configuration."""

    def test_app_config(self):
        """Test that the app config is properly configured."""
        app_config = apps.get_app_config("data")
        self.assertIsInstance(app_config, DataConfig)
        self.assertEqual(app_config.name, "data")
        self.assertEqual(app_config.verbose_name, "Data Layer")
