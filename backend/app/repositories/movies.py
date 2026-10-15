"""SQL for the movies. Every value from the request goes in as a parameter, never into the SQL text, and the
sort column comes from a fixed dictionary: ORDER BY can't be parameterized (ADR 0007)."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Connection, Double, RowMapping, case, cast, func, or_, select

from ..models import load_runs, movies
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
SORT_COLUMNS = {
    "rating": movies.c.weighted_rating,
    "year": movies.c.year,
    "votes": movies.c.votes,
    "duration": movies.c.duration,
    # Folded title without its leading symbols, in byte order: the same A-Z everywhere, whatever the collation of
    # the database. The titles made only of symbols have no key and go last either way (nulls_last below).
    "title": movies.c.title_sort.collate("C"),
}


@dataclass(frozen=True)
class MovieFilters:
    title: str | None = None
    genre: str | None = None
    countries: tuple[str, ...] = ()
    year_from: int | None = None
    year_to: int | None = None
    min_votes: int | None = None


def _matches(pattern: str) -> ColumnElement[bool]:
    return or_(*(column.like(pattern, escape="\\") for column in SEARCH_COLUMNS))


def _conditions(filters: MovieFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.title:
        conditions.append(_matches(f"%{like_escape(fold(filters.title))}%"))
    if filters.genre:
        conditions.append(movies.c.genres.contains([filters.genre]))
    if filters.countries:
        conditions.append(movies.c.countries.overlap(list(filters.countries)))
    if filters.year_from is not None:
        conditions.append(movies.c.year >= filters.year_from)
    if filters.year_to is not None:
        conditions.append(movies.c.year <= filters.year_to)
    if filters.min_votes is not None:
        conditions.append(movies.c.votes >= filters.min_votes)
    return conditions


def relevance(title: str) -> ColumnElement[float]:
    """Popularity on a log scale, plus 2 when a title is exactly the search and 1 when it starts with it.

    Popularity has to weigh: ranking exact matches first put an obscure film called "Godfather" (2.839 votes)
    above The Godfather.
    """
    query = fold(title)
    bonus = case(
        (or_(*(column == query for column in SEARCH_COLUMNS)), 2), (_matches(f"{like_escape(query)}%"), 1), else_=0
    )
    return func.log(cast(movies.c.votes + 1, Double)) + bonus


def find_movies(
    conn: Connection, filters: MovieFilters, sort: str, descending: bool, limit: int, offset: int
) -> tuple[Sequence[RowMapping], int]:
    """A page of movies and the total of the filtered list."""
    conditions = _conditions(filters)
    if sort == "relevance" and filters.title:
        order = [relevance(filters.title).desc()]
    else:
        column = SORT_COLUMNS[sort]
        order = [(column.desc() if descending else column.asc()).nulls_last()]
    # The id breaks ties, so the pagination is stable: no movie shows up on two pages.
    order.append(movies.c.imdb_title_id.asc())

    if not conditions:
        # Without filters, counting the 85.855 rows on every request costs 6-13 ms; the last load knows the total.
        rows = conn.execute(select(*SUMMARY_COLUMNS).order_by(*order).limit(limit).offset(offset)).mappings().all()
        return rows, loaded_movies(conn)

    stmt = select(*SUMMARY_COLUMNS, func.count().over().label("total")).where(*conditions)
    rows = conn.execute(stmt.order_by(*order).limit(limit).offset(offset)).mappings().all()
    if rows:
        return rows, rows[0]["total"]
    # A page past the end has no rows to carry the total, so it needs its own count.
    return rows, conn.execute(select(func.count()).select_from(movies).where(*conditions)).scalar_one()


def get_movie(conn: Connection, imdb_title_id: str) -> RowMapping | None:
    return conn.execute(select(movies).where(movies.c.imdb_title_id == imdb_title_id)).mappings().one_or_none()


def _item_counts(conn: Connection, column: ColumnElement[list[str]]) -> list[tuple[str, int]]:
    names = select(func.unnest(column).label("name")).subquery()
    count = func.count().label("movies")
    stmt = select(names.c.name, count).group_by(names.c.name).order_by(count.desc(), names.c.name)
    return [(row.name, row.movies) for row in conn.execute(stmt)]


def genre_counts(conn: Connection) -> list[tuple[str, int]]:
    return _item_counts(conn, movies.c.genres)


def country_counts(conn: Connection) -> list[tuple[str, int]]:
    return _item_counts(conn, movies.c.countries)


def last_load_id(conn: Connection) -> int | None:
    """The id of the last load: it changes only when the data changes."""
    return conn.execute(select(func.max(load_runs.c.id))).scalar()


def loaded_movies(conn: Connection) -> int:
    """Movies of the last load, or a count when there is no record of it."""
    loaded = conn.execute(select(load_runs.c.rows_loaded).order_by(load_runs.c.id.desc()).limit(1)).scalar()
    if loaded is not None:
        return loaded
    return conn.execute(select(func.count()).select_from(movies)).scalar_one()
