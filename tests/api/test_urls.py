from django.test import TestCase

from api.views.edit_views import EditView, ResultView, SectionHeadingsView


class TestDjangoUrls(TestCase):
    """Test Django URLs configuration."""

    def test_admin_url_resolution(self):
        """Test that admin URL resolves correctly."""
        from EditEngine.urls import urlpatterns

        # We expect 8 URL patterns: health/, admin/, api/, api/schema/, api/docs/, api/redoc/, healthz/, ''
        self.assertEqual(len(urlpatterns), 8)

        # Test admin URL pattern (health check is now at index 0)
        admin_url = urlpatterns[1]
        self.assertEqual(admin_url.pattern._route, "admin/")

    def test_edit_urls_inclusion(self):
        """Test that edit app URLs are included."""
        from EditEngine.urls import urlpatterns

        # Test include URL pattern (api is now at index 2)
        include_url = urlpatterns[2]
        self.assertEqual(include_url.pattern._route, "api/")

    def test_edit_url_resolution(self):
        """Test that edit URLs resolve correctly."""
        from api.urls import urlpatterns

        self.assertEqual(len(urlpatterns), 5)

        # Test edit URL pattern
        edit_url = urlpatterns[0]
        self.assertEqual(edit_url.pattern._route, "edit/<str:editing_mode>")

        # Test results URL pattern
        results_url = urlpatterns[1]
        self.assertEqual(results_url.pattern._route, "results/<str:task_id>")

        # Test section-headings URL pattern
        section_headings_url = urlpatterns[2]
        self.assertEqual(section_headings_url.pattern._route, "section-headings")

    def test_edit_view_class(self):
        """Test that EditView is properly imported and used."""
        from api.urls import urlpatterns

        edit_url = urlpatterns[0]
        self.assertEqual(edit_url.callback.view_class, EditView)
        self.assertEqual(edit_url.name, "edit")

    def test_results_view_class(self):
        """Test that ResultView is properly imported and used."""
        from api.urls import urlpatterns

        results_url = urlpatterns[1]
        self.assertEqual(results_url.callback.view_class, ResultView)
        self.assertEqual(results_url.name, "results")

    def test_section_headings_view_class(self):
        """Test that SectionHeadingsView is properly imported and used."""
        from api.urls import urlpatterns

        section_headings_url = urlpatterns[2]
        self.assertEqual(section_headings_url.callback.view_class, SectionHeadingsView)
        self.assertEqual(section_headings_url.name, "section-headings")
