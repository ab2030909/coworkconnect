import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coworkconnect.settings")

# Vercel's Python runtime uses this top-level WSGI app as the serverless entrypoint.
app = get_wsgi_application()
