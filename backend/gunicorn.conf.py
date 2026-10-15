"""Gunicorn settings. Each one can be changed with an environment variable."""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
accesslog = "-"
errorlog = "-"
