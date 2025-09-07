"""
WSGI config for EditEngine project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from dotenv import load_dotenv
from configurations.wsgi import get_wsgi_application

# Load environment variables from .env file
load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EditEngine.settings")
os.environ.setdefault("DJANGO_CONFIGURATION", "Production")

application = get_wsgi_application()
