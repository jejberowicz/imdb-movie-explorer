"""Load the CSV into the movies table.

This first version takes the columns that the list and the search need and replaces the table in a single
transaction. The cleaning rules of ADR 0003 come in Phase 2.
"""

import csv
import gzip
import re
import statistics
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text

from ..text import fold

COLUMNS = (
    "imdb_title_id",
    "original_title",
    "italian_title",
    "original_title_search",
    "italian_title_search",
    "year",
    "genres",
    "directors",
    "duration",
    "avg_vote",
    "votes",
    "weighted_rating",
)
_YEAR = re.compile(r"\b([0-9]{4})\b")


def read_csv(path: Path) -> list[dict[str, str]]:
    """The rows of the CSV; a .gz file is decompressed on the fly."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def weighted_rating(avg: float, votes: int, mean: float, min_votes: float) -> float:
    """IMDb-style weighted rating (ADR 0008): the movie's rating pulled towards the mean until it has votes."""
    return votes / (votes + min_votes) * avg + min_votes / (votes + min_votes) * mean


def build_records(rows: list[dict[str, str]]) -> list[tuple[Any, ...]]:
    avgs = [float(row["avg_vote"]) for row in rows]
    votes = [int(row["votes"]) for row in rows]
    mean = statistics.fmean(avgs)
    min_votes = statistics.quantiles(votes, n=100, method="inclusive")[89]
    records = []
    for row, avg, count in zip(rows, avgs, votes, strict=True):
        year = _YEAR.search(row["year"])
        records.append(
            (
                row["imdb_title_id"],
                row["original_title"],
                row["title"],
                fold(row["original_title"]),
                fold(row["title"]),
                int(year.group(1)) if year else None,
                split_list(row["genre"]),
                split_list(row["director"]),
                int(row["duration"]),
                avg,
                count,
                weighted_rating(avg, count, mean, min_votes),
            )
        )
    return records


def load(engine: Engine, path: Path) -> int:
    """Replace the movies with the CSV's, in one transaction: readers keep the old data until the commit."""
    records = build_records(read_csv(path))
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE movies"))
        cursor = conn.connection.dbapi_connection.cursor()
        with cursor.copy(f"COPY movies ({', '.join(COLUMNS)}) FROM STDIN") as copy:
            for record in records:
                copy.write_row(record)
    return len(records)
