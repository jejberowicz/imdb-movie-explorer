"""One SQLAlchemy engine per app, built from the configuration."""

from flask import Flask, current_app
from sqlalchemy import Engine, create_engine


def init_engine(app: Flask, url: str) -> None:
    app.extensions["engine"] = create_engine(url, pool_pre_ping=True)


def get_engine() -> Engine:
    return current_app.extensions["engine"]
