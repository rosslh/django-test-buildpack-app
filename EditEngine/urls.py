"""
URL configuration for EditEngine project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.staticfiles import views as staticfiles_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include, re_path
from .views import healthz, home
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from client.views import index_view


def health_check(request):
    from django.http import HttpResponse

    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("healthz/", healthz, name="healthz"),
]

# Always serve static files for local development/testing
urlpatterns += staticfiles_urlpatterns()

# Static file serving for assets not handled by WhiteNoise
urlpatterns.append(
    re_path(
        r"^(?!api/)(?P<path>.*\.(?:png|svg|jpg|jpeg|gif|ico|js|css))$",
        staticfiles_views.serve,
    )
)

# Add specific routes for the SPA
# Note: Using re_path with explicit pattern to avoid redirect issues on Toolforge
urlpatterns.extend([
    path('', index_view, name='home'),  # Root path
    # Only catch paths that don't start with api/, admin/, health/, or static files
    re_path(r'^(?!api/|admin/|health/|static/).*$', index_view, name='index'),
])
