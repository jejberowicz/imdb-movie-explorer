"""Gunicorn settings. Each one can be changed with an environment variable."""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
# The control socket (gunicornc, since Gunicorn 25.1) goes unused here, and the container's filesystem is
# read-only: it would only fail to start, and it is one more way in.
control_socket_disable = True
accesslog = "-"
errorlog = "-"
