"""Shared fixtures. The tests run against a real PostgreSQL, because the search depends on its features.

TEST_DATABASE_URL has to point to a database that the tests can wipe: each session drops its schema and
rebuilds it with the Alembic migrations, the same way production gets it.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from flask.testing import FlaskClient
from sqlalchemy import Engine, create_engine, text

from app import create_app
from app.config import Settings
from app.etl.load import load

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_CSV = FIXTURES / "movies_sample.csv"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.exit("Set TEST_DATABASE_URL to a PostgreSQL database that the tests can wipe.", returncode=2)
    return url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["configure_logger"] = False
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def sample_db(engine: Engine) -> Engine:
    """The database loaded with the hand-picked sample: 16 real movies that cover the search cases."""
    load(engine, SAMPLE_CSV)
    return engine


@pytest.fixture
def client(sample_db: Engine, database_url: str) -> FlaskClient:
    app = create_app(Settings(database_url=database_url))
    app.config["TESTING"] = True
    return app.test_client()
