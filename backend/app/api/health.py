"""Health check: answers as long as the process is up, without touching the database."""

from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel

health_bp = APIBlueprint("health", __name__, url_prefix="/health", abp_tags=[Tag(name="health")])


class HealthStatus(BaseModel):
    status: str


@health_bp.get("", responses={200: HealthStatus})
def liveness():
    """The process is up."""
    return {"status": "ok"}
