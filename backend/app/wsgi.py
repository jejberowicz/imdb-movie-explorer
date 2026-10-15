"""Entry point for Gunicorn: `gunicorn app.wsgi:app`."""

from . import create_app

app = create_app()
