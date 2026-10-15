"""Health checks: liveness (the process answers) and readiness (the database answers and has data)."""

import logging

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from ..errors import Problem, problem
from ..services import movies as service

logger = logging.getLogger(__name__)
health_bp = APIBlueprint("health", __name__, url_prefix="/health", abp_tags=[Tag(name="health")])


class HealthStatus(BaseModel):
    status: str


class ReadyStatus(HealthStatus):
    movies: int


@health_bp.get("", responses={200: HealthStatus})
def liveness():
    """The process is up. It doesn't touch the database."""
    return {"status": "ok"}


@health_bp.get("/ready", responses={200: ReadyStatus, 503: Problem})
def readiness():
    """The database answers and has a complete load. Docker uses it as the healthcheck of the API."""
    try:
        movies = service.loaded_movies()
    except SQLAlchemyError:
        logger.exception("The database is not answering")
        return problem(503, "The database is not available.")
    if movies == 0:
        return problem(503, "No movies loaded yet.")
    return {"status": "ready", "movies": movies}
