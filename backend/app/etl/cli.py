"""`flask seed PATH`: the command that loads the CSV. Docker Compose runs it once, before the API starts."""

from pathlib import Path

import click
from flask.cli import with_appcontext

from ..db import get_engine
from .load import load


@click.command("seed")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@with_appcontext
def seed_command(path: Path) -> None:
    """Load the movies CSV (plain or .gz) into the database."""
    count = load(get_engine(), path)
    click.echo(f"Loaded {count} movies from {path.name}")
