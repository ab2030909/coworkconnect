import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coworkconnect.settings")

# Vercel's Python runtime expects a top-level WSGI or ASGI variable named `app`.
app = get_wsgi_application()
