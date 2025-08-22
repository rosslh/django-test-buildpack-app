"""Tests for Services app configuration."""

from django.apps import apps
from django.test import TestCase

from services.apps import ServicesConfig


class TestServicesConfig(TestCase):
    """Test Services app configuration."""

    def test_app_config(self):
        """Test that the app config is properly configured."""
        app_config = apps.get_app_config("services")
        self.assertIsInstance(app_config, ServicesConfig)
        self.assertEqual(app_config.name, "services")
        self.assertEqual(app_config.verbose_name, "Services Layer")
