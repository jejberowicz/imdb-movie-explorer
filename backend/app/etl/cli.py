"""`flask seed PATH`: the command that loads the CSV. Docker Compose runs it once, before the API starts."""

from pathlib import Path

import click
from flask.cli import with_appcontext

from ..db import get_engine
from .load import LoadError, load


@click.command("seed")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Load even if the same file was already loaded.")
@with_appcontext
def seed_command(path: Path, force: bool) -> None:
    """Load the movies CSV (plain or .gz) into the database, applying the cleaning rules."""
    try:
        summary = load(get_engine(), path, force=force)
    except LoadError as error:
        raise click.ClickException(str(error)) from error
    click.echo(summary.report())
