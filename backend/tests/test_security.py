"""Security headers, rate limiting and the client IP behind the proxy."""

import pytest
from flask.testing import FlaskClient
from sqlalchemy import Engine

from app import create_app
from app.config import Settings


def make_client(database_url: str, **settings) -> FlaskClient:
    app = create_app(Settings(database_url=database_url, **settings))
    app.config["TESTING"] = True
    return app.test_client()


def test_json_responses_carry_the_security_headers(client: FlaskClient) -> None:
    response = client.get("/movies?page_size=1")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_errors_carry_them_too(client: FlaskClient) -> None:
    response = client.get("/movies?page=0")
    assert response.status_code == 400
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_swagger_ui_keeps_its_scripts(client: FlaskClient) -> None:
    response = client.get("/docs/swagger")
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_too_many_requests_get_a_429_with_retry_after(sample_db: Engine, database_url: str) -> None:
    client = make_client(database_url, rate_limit="3 per minute")
    assert [client.get("/genres").status_code for _ in range(3)] == [200, 200, 200]
    response = client.get("/genres")
    assert response.status_code == 429
    assert response.mimetype == "application/problem+json"
    assert response.get_json()["title"] == "Too Many Requests"
    assert int(response.headers["Retry-After"]) > 0


def test_health_checks_are_never_limited(sample_db: Engine, database_url: str) -> None:
    client = make_client(database_url, rate_limit="1 per minute")
    assert {client.get("/health/ready").status_code for _ in range(5)} == {200}


@pytest.mark.parametrize(("proxy_hops", "separate"), [(1, True), (0, False)])
def test_the_client_ip_comes_from_the_proxy_only_when_there_is_one(
    sample_db: Engine, database_url: str, proxy_hops: int, separate: bool
) -> None:
    """Behind nginx, each client has its own limit. Without a proxy, a made-up X-Forwarded-For changes nothing."""
    client = make_client(database_url, rate_limit="1 per minute", proxy_hops=proxy_hops)
    first = client.get("/genres", headers={"X-Forwarded-For": "203.0.113.1"})
    second = client.get("/genres", headers={"X-Forwarded-For": "203.0.113.2"})
    assert first.status_code == 200
    assert (second.status_code == 200) is separate
