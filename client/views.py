from django.shortcuts import render


def index_view(request):
    """Serves the frontend application."""
    return render(request, "client/index.html")