"""Movie use cases. No HTTP here: the routes translate requests and responses."""

import math
from collections.abc import Callable
from typing import Any

from flask import current_app
from sqlalchemy import Connection

from ..countries import FORMER, map_code
from ..db import get_engine
from ..repositories import movies as repository
from ..repositories.movies import MovieFilters
from ..schemas.movies import (
    CountryCount,
    CountryList,
    GenreCount,
    GenreList,
    MovieDetail,
    MovieListQuery,
    MoviePage,
    MovieSummary,
)


def list_movies(query: MovieListQuery) -> MoviePage:
    filters = MovieFilters(
        title=query.title,
        genre=query.genre,
        countries=tuple(query.country),
        year_from=query.year_from,
        year_to=query.year_to,
        min_votes=query.min_votes,
    )
    # Defaults of ADR 0007 and 0008: relevance when searching, the weighted rating otherwise.
    sort = query.sort or ("relevance" if query.title else "rating")
    descending = (query.order or ("asc" if sort == "title" else "desc")) == "desc"
    offset = (query.page - 1) * query.page_size
    with get_engine().connect() as conn:
        rows, total = repository.find_movies(conn, filters, sort, descending, limit=query.page_size, offset=offset)
    return MoviePage(
        items=[MovieSummary.model_validate(dict(row)) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
        total_pages=math.ceil(total / query.page_size),
    )


def get_movie(imdb_title_id: str) -> MovieDetail | None:
    with get_engine().connect() as conn:
        row = repository.get_movie(conn, imdb_title_id)
    if row is None:
        return None
    data: dict[str, Any] = dict(row)

    def money(prefix: str) -> dict[str, Any] | None:
        amount = data.pop(f"{prefix}_amount")
        currency = data.pop(f"{prefix}_currency")
        return {"amount": amount, "currency": currency} if amount is not None else None

    return MovieDetail(
        **data,
        budget=money("budget"),
        usa_gross_income=money("usa_gross"),
        worldwide_gross_income=money("worldwide_gross"),
        imdb_url=f"https://www.imdb.com/title/{imdb_title_id}/",
    )


def _per_load[T](name: str, compute: Callable[[Connection], T]) -> T:
    """The result of `compute`, kept until the next load: genres and countries only change with new data, and
    counting them takes ~40 ms over the 85.855 movies, while asking for the last load takes a fraction of 1 ms."""
    cache: dict[str, tuple[int, Any]] = current_app.extensions.setdefault("per_load_cache", {})
    with get_engine().connect() as conn:
        load_id = repository.last_load_id(conn)
        cached = cache.get(name)
        if load_id is not None and cached is not None and cached[0] == load_id:
            return cached[1]
        value = compute(conn)
    if load_id is not None:
        cache[name] = (load_id, value)
    return value


def list_genres() -> GenreList:
    counts = _per_load("genres", repository.genre_counts)
    return GenreList(items=[GenreCount(name=name, movies=count) for name, count in counts])


def list_countries() -> CountryList:
    counts = _per_load("countries", repository.country_counts)
    return CountryList(
        items=[
            CountryCount(name=name, movies=count, map_code=map_code(name), former=name in FORMER)
            for name, count in counts
        ]
    )


def loaded_movies() -> int:
    """How many movies the last load left. Raises if the database can't answer."""
    with get_engine().connect() as conn:
        return repository.loaded_movies(conn)
