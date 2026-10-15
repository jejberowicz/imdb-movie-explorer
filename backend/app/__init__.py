"""Flask application factory."""

from flask_openapi3 import Info, OpenAPI

from .api.catalog import catalog_bp
from .api.health import health_bp
from .api.movies import movies_bp
from .config import Settings
from .db import init_engine
from .errors import Problem, register_error_handlers, validation_problem
from .etl.cli import seed_command


def create_app(settings: Settings | None = None) -> OpenAPI:
    settings = settings or Settings.from_env()
    app = OpenAPI(
        __name__,
        info=Info(
            title="IMDb Movie Explorer API",
            version="1.0.0",
            description="The 85.855 movies of the IMDb CSV: list, search by title, filters and detail.",
        ),
        doc_prefix="/docs",
        validation_error_status=400,
        validation_error_model=Problem,
        validation_error_callback=validation_problem,
    )
    # Keep the field order of the models and the accents as they are in the JSON output.
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    init_engine(app, settings.database_url)
    register_error_handlers(app)
    app.register_api(health_bp)
    app.register_api(movies_bp)
    app.register_api(catalog_bp)
    app.cli.add_command(seed_command)
    return app
