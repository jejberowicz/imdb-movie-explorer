"""Errors as RFC 9457 Problem Details: the same JSON shape for every error, never a stack trace."""

import logging
from http import HTTPStatus

from flask import Flask, Response, jsonify
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ProblemError(BaseModel):
    parameter: str | None
    detail: str


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[ProblemError] | None = None


def problem(status: int, detail: str | None = None, errors: list[ProblemError] | None = None) -> Response:
    body = Problem(title=HTTPStatus(status).phrase, status=status, detail=detail, errors=errors)
    response = jsonify(body.model_dump(exclude_none=True))
    response.status_code = status
    response.mimetype = "application/problem+json"
    return response


def validation_problem(error: ValidationError) -> Response:
    """Invalid request parameters: 400, with the parameter and the reason of each problem (ADR 0007)."""
    errors = [
        ProblemError(parameter=".".join(str(part) for part in item["loc"]) or None, detail=item["msg"])
        for item in error.errors()
    ]
    return problem(400, "Invalid request parameters.", errors)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> Response:
        return problem(error.code or 500, error.description)

    @app.errorhandler(Exception)
    def unexpected_error(error: Exception) -> Response:
        # The details go to the log, never to the response.
        logger.exception("Unexpected error", exc_info=error)
        return problem(500, "Unexpected error.")
