"""SQL for the movies table. Every value from the request goes in as a parameter, never into the SQL text."""

from collections.abc import Sequence

from sqlalchemy import ColumnElement, Connection, RowMapping, case, func, or_, select

from ..models import movies
from ..text import fold, like_escape

SUMMARY_COLUMNS = (
    movies.c.imdb_title_id,
    movies.c.original_title,
    movies.c.year,
    movies.c.genres,
    movies.c.directors,
    movies.c.duration,
    movies.c.avg_vote,
    movies.c.votes,
    movies.c.weighted_rating,
)
SEARCH_COLUMNS = (movies.c.original_title_search, movies.c.italian_title_search)


def _matches(pattern: str) -> ColumnElement[bool]:
    return or_(*(column.like(pattern, escape="\\") for column in SEARCH_COLUMNS))


def find_movies(conn: Connection, title: str | None, limit: int, offset: int) -> tuple[Sequence[RowMapping], int]:
    """A page of movies and the total. With a title, by relevance; without one, by weighted rating."""
    stmt = select(*SUMMARY_COLUMNS, func.count().over().label("total"))
    conditions: list[ColumnElement[bool]] = []
    if title:
        query = fold(title)
        conditions.append(_matches(f"%{like_escape(query)}%"))
        relevance = case(
            (or_(*(column == query for column in SEARCH_COLUMNS)), 0),
            (_matches(f"{like_escape(query)}%"), 1),
            else_=2,
        )
        stmt = stmt.where(*conditions).order_by(relevance, movies.c.votes.desc(), movies.c.imdb_title_id)
    else:
        stmt = stmt.order_by(movies.c.weighted_rating.desc(), movies.c.imdb_title_id)
    rows = conn.execute(stmt.limit(limit).offset(offset)).mappings().all()
    if rows:
        return rows, rows[0]["total"]
    # A page past the end has no rows to carry the total, so it needs its own count.
    total = conn.execute(select(func.count()).select_from(movies).where(*conditions)).scalar_one()
    return rows, total
