"""Movie use cases. No HTTP here: the routes translate requests and responses."""

import math

from ..db import get_engine
from ..repositories import movies as repository
from ..schemas.movies import MovieListQuery, MoviePage, MovieSummary


def list_movies(query: MovieListQuery) -> MoviePage:
    offset = (query.page - 1) * query.page_size
    with get_engine().connect() as conn:
        rows, total = repository.find_movies(conn, query.title, limit=query.page_size, offset=offset)
    return MoviePage(
        items=[MovieSummary.model_validate(dict(row)) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
        total_pages=math.ceil(total / query.page_size),
    )
