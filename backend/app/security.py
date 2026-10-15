"""Rate limiting and security headers for every response (docs/security-plan.md)."""

from flask import Flask, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Settings

HEADERS = {
    # The browser must not guess another type for a JSON response.
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
LOOPBACK = {"127.0.0.1", "::1"}
UNMATCHED = "<no route>"
# The JSON responses load nothing and can't be framed. Swagger UI (/docs) needs its own scripts, so it is left out.
API_CSP = "default-src 'none'; frame-ancestors 'none'"


def init_security(app: Flask, settings: Settings) -> None:
    if settings.proxy_hops:
        # Behind nginx, the client IP comes in X-Forwarded-For; without this, every client would share one limit.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=settings.proxy_hops, x_proto=settings.proxy_hops)

    # In memory, each Gunicorn worker counts on its own: the real limit is the limit times the workers. Enough
    # for one machine; with several, the storage would be Redis (storage_uri="redis://...").
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[settings.rate_limit],
        storage_uri="memory://",
        headers_enabled=True,
        # Flask-Limiter exempts a request without an endpoint, so 404s and 405s had no limit at all. They share
        # one count per client instead, like any route.
        request_identifier=lambda: request.endpoint or UNMATCHED,
    )

    @limiter.request_filter
    def docker_health_checks() -> bool:
        # Docker asks every few seconds from inside the container; a limit there could mark a healthy API as down.
        # Only that one is exempt: through nginx, /health/ready is public and queries the database.
        return request.path.startswith("/health") and request.remote_addr in LOOPBACK

    @app.after_request
    def security_headers(response: Response) -> Response:
        for name, value in HEADERS.items():
            response.headers.setdefault(name, value)
        if not request.path.startswith("/docs"):
            response.headers.setdefault("Content-Security-Policy", API_CSP)
        return response
