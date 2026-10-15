"""Flask application factory."""

from flask_openapi3 import Info, OpenAPI

from .config import Settings
from .db import init_engine
from .etl.cli import seed_command


def create_app(settings: Settings | None = None) -> OpenAPI:
    settings = settings or Settings.from_env()
    app = OpenAPI(
        __name__,
        info=Info(title="IMDb Movie Explorer API", version="1.0.0"),
        doc_prefix="/docs",
        validation_error_status=400,
    )
    # Keep the field order of the models and the accents as they are in the JSON output.
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    init_engine(app, settings.database_url)
    app.cli.add_command(seed_command)
    return app
