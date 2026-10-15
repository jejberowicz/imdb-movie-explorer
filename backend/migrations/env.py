"""Alembic environment: migrations run against DATABASE_URL, or against a connection that the tests pass in."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine

from app.config import Settings
from app.models import metadata

config = context.config
if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)


def run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported: run them against a database.")

if (given := config.attributes.get("connection")) is not None:
    run(given)
else:
    with create_engine(Settings.from_env().database_url).connect() as connection:
        run(connection)
        connection.commit()
