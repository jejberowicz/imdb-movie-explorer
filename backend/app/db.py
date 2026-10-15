"""One SQLAlchemy engine per app, built from the configuration."""

from flask import Flask, current_app
from sqlalchemy import Engine, create_engine

# Seconds to wait for the database to answer a new connection. libpq waits forever by default, so a database that
# accepts the connection and never answers would tie up a Gunicorn worker until its timeout kills it.
CONNECT_TIMEOUT = 3


def init_engine(app: Flask, url: str) -> None:
    app.extensions["engine"] = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": CONNECT_TIMEOUT})


def get_engine() -> Engine:
    return current_app.extensions["engine"]
