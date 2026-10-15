"""Load the movies CSV into PostgreSQL, applying the cleaning rules of ADR 0003.

- A row that can't be read doesn't stop the load: it is set aside in load_rejections, with its reason.
- If the rejected rows go over a threshold (1% by default), nothing is written and the load fails.
- The same file as the last load (same SHA-256) means there is nothing to do.
- Otherwise the movies are replaced in one transaction with DELETE and COPY: readers see the old data until the
  commit, and running the load twice leaves the same state.
"""

import csv
import gzip
import hashlib
import io
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import IO, Any

from sqlalchemy import Connection, Engine, insert, select, text

from ..models import load_rejections, load_runs
from ..text import fold
from .parsers import (
    SMALLINT_MAX,
    InvalidValue,
    Money,
    parse_count,
    parse_id,
    parse_list,
    parse_money,
    parse_optional_text,
    parse_rating,
    parse_required_text,
    parse_score,
    parse_whole,
    parse_year,
    repair_mojibake,
)

CSV_COLUMNS = (
    "imdb_title_id", "title", "original_title", "year", "date_published", "genre", "duration", "country",
    "language", "director", "writer", "production_company", "actors", "description", "avg_vote", "votes",
    "budget", "usa_gross_income", "worlwide_gross_income", "metascore", "reviews_from_users",
    "reviews_from_critics",
)  # fmt: skip
MOVIE_COLUMNS = (
    "imdb_title_id", "original_title", "italian_title", "original_title_search", "italian_title_search", "year",
    "genres", "directors", "duration", "avg_vote", "votes", "weighted_rating", "countries", "languages", "writers",
    "actors", "production_company", "description", "metascore", "reviews_from_users", "reviews_from_critics",
    "budget_amount", "budget_currency", "usa_gross_amount", "usa_gross_currency", "worldwide_gross_amount",
    "worldwide_gross_currency",
)  # fmt: skip
# Lists of the CSV and the column where each one goes
LIST_COLUMNS = {"countries": "country", "languages": "language", "writers": "writer", "actors": "actors"}
MONEY_COLUMNS = {"budget": "budget", "usa_gross": "usa_gross_income", "worldwide_gross": "worlwide_gross_income"}
MAX_REJECTED_SHARE = 0.01


class LoadError(Exception):
    """The load was cancelled and nothing was written."""


@dataclass
class Rejection:
    line_number: int
    imdb_title_id: str | None
    reason: str
    raw: dict[str, Any]


@dataclass
class LoadSummary:
    source: str
    sha256: str
    rows_read: int = 0
    rows_loaded: int = 0
    rejections: Counter[str] = field(default_factory=Counter)
    corrections: Counter[str] = field(default_factory=Counter)
    mean_vote: float = 0.0
    min_votes: float = 0.0
    skipped: bool = False

    @property
    def rows_rejected(self) -> int:
        return sum(self.rejections.values())

    def report(self) -> str:
        if self.skipped:
            return f"{self.source} is already loaded (same SHA-256); nothing to do."
        lines = [
            f"Read {self.rows_read} rows from {self.source}: {self.rows_loaded} loaded, {self.rows_rejected} rejected."
        ]
        lines += [f"  rejected, {reason}: {count}" for reason, count in sorted(self.rejections.items())]
        lines += [f"  corrected, {code}: {count}" for code, count in sorted(self.corrections.items())]
        if self.rows_loaded:
            lines.append(f"Weighted rating: mean vote {self.mean_vote:.2f}, minimum votes {self.min_votes:.0f}.")
        return "\n".join(lines)


def weighted_rating(avg: float, votes: int, mean: float, min_votes: float) -> float:
    """IMDb-style weighted rating (ADR 0008): the movie's rating, pulled towards the mean until it has votes."""
    return votes / (votes + min_votes) * avg + min_votes / (votes + min_votes) * mean


def rating_constants(movies: list[dict[str, Any]]) -> tuple[float, float]:
    """C, the mean rating, and m, the 90th percentile of the votes (linear interpolation, as percentile_cont)."""
    votes = [movie["votes"] for movie in movies]
    min_votes = statistics.quantiles(votes, n=100, method="inclusive")[89] if len(votes) > 1 else votes[0]
    return statistics.fmean(movie["avg_vote"] for movie in movies), min_votes


def clean_row(row: dict[str, str], max_year: int) -> tuple[dict[str, Any], Counter[str]]:
    """The clean values of one row and the corrections made to it.

    A required field that can't be read raises InvalidValue and rejects the row. An optional one is dropped with
    a note instead, so a movie is not lost over a secondary piece of data.
    """
    corrections: Counter[str] = Counter()

    def note(*codes: str | None) -> None:
        corrections.update(code for code in codes if code)

    def optional(column: str, parse: Any, value: str) -> Any:
        try:
            result, code = parse(value)
        except InvalidValue:
            note(f"invalid_{column}_dropped")
            return None
        note(code)
        return result

    year, code = parse_year(row["year"], max_year)
    note(code)
    genres, codes = parse_list(row["genre"])
    note(*codes)
    if not genres:
        raise InvalidValue("no genre")
    original_title = parse_required_text(row["original_title"], "original_title")
    italian_title = parse_required_text(row["title"], "title")
    movie: dict[str, Any] = {
        "imdb_title_id": parse_id(row["imdb_title_id"]),
        "original_title": original_title,
        "italian_title": italian_title,
        "original_title_search": fold(original_title),
        "italian_title_search": fold(italian_title),
        "year": year,
        "genres": genres,
        "duration": parse_count(row["duration"], "duration", minimum=1, maximum=SMALLINT_MAX),
        "avg_vote": parse_rating(row["avg_vote"]),
        "votes": parse_count(row["votes"], "votes"),
        "production_company": parse_optional_text(row["production_company"]),
        "metascore": optional("metascore", parse_score, row["metascore"]),
        "reviews_from_users": optional("reviews_from_users", parse_whole, row["reviews_from_users"]),
        "reviews_from_critics": optional("reviews_from_critics", parse_whole, row["reviews_from_critics"]),
    }
    movie["directors"], codes = parse_list(row["director"])
    note(*codes)
    for column, source in LIST_COLUMNS.items():
        movie[column], codes = parse_list(row[source])
        note(*codes)
    description = parse_optional_text(row["description"])
    if description is not None:
        description, code = repair_mojibake(description)
        note(code)
    movie["description"] = description
    for column, source in MONEY_COLUMNS.items():
        money: Money | None = optional(column, parse_money, row[source])
        movie[f"{column}_amount"], movie[f"{column}_currency"] = money if money else (None, None)
    return movie, corrections


def open_csv_bytes(path: Path) -> IO[bytes]:
    """The CSV as a stream of bytes; a .gz file is decompressed on the fly, without loading it whole."""
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def csv_sha256(path: Path) -> str:
    """SHA-256 of the CSV itself (decompressed): the same value the README publishes for the original file."""
    digest = hashlib.sha256()
    with open_csv_bytes(path) as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(
    engine: Engine,
    path: Path,
    *,
    force: bool = False,
    max_rejected_share: float = MAX_REJECTED_SHARE,
    today: date | None = None,
) -> LoadSummary:
    summary = LoadSummary(source=path.name, sha256=csv_sha256(path))
    if not force and _last_loaded_sha256(engine) == summary.sha256:
        summary.skipped = True
        return summary
    with open_csv_bytes(path) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
        movies, rejected = _clean_rows(csv.DictReader(stream), path, summary, (today or date.today()).year)

    if summary.rows_read and summary.rows_rejected / summary.rows_read > max_rejected_share:
        raise LoadError(
            f"{summary.rows_rejected} of {summary.rows_read} rows rejected, over the {max_rejected_share:.0%} "
            f"threshold: nothing was loaded.\n{summary.report()}"
        )
    if not movies:
        raise LoadError(f"{path.name} has no valid rows: nothing was loaded.")

    summary.mean_vote, summary.min_votes = rating_constants(movies)
    for movie in movies:
        movie["weighted_rating"] = weighted_rating(
            movie["avg_vote"], movie["votes"], summary.mean_vote, summary.min_votes
        )
    summary.rows_loaded = len(movies)
    with engine.begin() as conn:
        _write(conn, movies, rejected, summary)
    # The deleted rows take space until a vacuum, and the planner needs statistics of the new ones. TRUNCATE false:
    # by default VACUUM ends by cutting the empty pages off the file, with a lock that does block readers. It
    # can't run inside a transaction.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM (TRUNCATE false, ANALYZE) movies"))
    return summary


def _clean_rows(
    reader: csv.DictReader, path: Path, summary: LoadSummary, max_year: int
) -> tuple[list[dict[str, Any]], list[Rejection]]:
    """Clean every row: valid ones become movies, the rest rejections with their reason."""
    missing = set(CSV_COLUMNS) - set(reader.fieldnames or ())
    if missing:
        raise LoadError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    movies: list[dict[str, Any]] = []
    rejected: list[Rejection] = []
    seen: set[str] = set()
    for row in reader:
        summary.rows_read += 1
        try:
            if None in row or None in row.values():
                raise InvalidValue("wrong number of fields")
            movie, corrections = clean_row(row, max_year)
            if movie["imdb_title_id"] in seen:
                raise InvalidValue("duplicate imdb_title_id")
        except InvalidValue as error:
            summary.rejections[str(error)] += 1
            rejected.append(Rejection(reader.line_num, row.get("imdb_title_id"), str(error), _raw(row)))
            continue
        seen.add(movie["imdb_title_id"])
        summary.corrections.update(corrections)
        movies.append(movie)
    return movies, rejected


def _write(conn: Connection, movies: list[dict[str, Any]], rejected: list[Rejection], summary: LoadSummary) -> None:
    run_id = conn.execute(
        insert(load_runs)
        .values(
            source=summary.source,
            sha256=summary.sha256,
            rows_read=summary.rows_read,
            rows_loaded=summary.rows_loaded,
            rows_rejected=summary.rows_rejected,
            corrections=dict(summary.corrections),
            mean_vote=summary.mean_vote,
            min_votes=summary.min_votes,
        )
        .returning(load_runs.c.id)
    ).scalar_one()
    if rejected:
        conn.execute(
            insert(load_rejections),
            [
                {"run_id": run_id, "line_number": r.line_number, "imdb_title_id": r.imdb_title_id, "reason": r.reason,
                 "raw": r.raw}
                for r in rejected
            ],
        )  # fmt: skip
    # DELETE and not TRUNCATE: TRUNCATE locks the table even for readers, so the API would wait, and fail after
    # its statement_timeout, until the load commits. With DELETE, readers keep seeing the old rows meanwhile.
    conn.execute(text("DELETE FROM movies"))
    cursor = conn.connection.dbapi_connection.cursor()
    with cursor.copy(f"COPY movies ({', '.join(MOVIE_COLUMNS)}) FROM STDIN") as copy:
        for movie in movies:
            copy.write_row([movie[column] for column in MOVIE_COLUMNS])


def _last_loaded_sha256(engine: Engine) -> str | None:
    with engine.connect() as conn:
        return conn.execute(select(load_runs.c.sha256).order_by(load_runs.c.id.desc()).limit(1)).scalar_one_or_none()


def _raw(row: dict[str | None, Any]) -> dict[str, Any]:
    """The row as it came, for load_rejections. Extra fields (under the None key) are kept apart."""
    raw = {key: value for key, value in row.items() if key is not None}
    if None in row:
        raw["_extra_fields"] = row[None]
    return raw
