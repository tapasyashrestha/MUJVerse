"""MUJVERSE ASGI application."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mujverse.config.settings")
application = get_asgi_application()
