"""A broken CSV must never break the load: each row is loaded or rejected with its reason, and a file that can't
be read as CSV stops with a clear LoadError, writing nothing."""

import csv
import random
import string
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, func, select

from app.etl.load import CSV_COLUMNS, LoadError, clean_row, load
from app.etl.parsers import InvalidValue
from app.models import movies
from tests.conftest import SAMPLE_CSV
from tests.test_load import movie, write_csv


def sample_rows(count: int) -> list[dict[str, str]]:
    with SAMPLE_CSV.open(encoding="utf-8", newline="") as sample:
        return list(csv.DictReader(sample))[:count]


class TestUnclosedQuote:
    def write(self, path: Path) -> Path:
        """Five movies; the description of the second one opens a quote that never closes."""
        write_csv(path, *({"imdb_title_id": f"tt90001{n:02d}", "description": f"Plot {n}"} for n in range(5)))
        text = path.read_text(encoding="utf-8").replace(",Plot 1,", ',"Plot 1,', 1)
        path.write_text(text, encoding="utf-8")
        return path

    def test_the_swallowed_rows_count_as_rejected(self, empty_db: Engine, tmp_path: Path) -> None:
        """The quote merges the next rows into one record: before, they vanished as a single rejection."""
        summary = load(empty_db, self.write(tmp_path / "quote.csv"), max_rejected_share=1)
        assert summary.rows_read == 5
        assert summary.rows_loaded + summary.rows_rejected == 5
        assert summary.rows_rejected >= 2
        assert set(summary.rejections) <= {"line break inside a field", "wrong number of fields"}

    def test_they_reach_the_threshold(self, empty_db: Engine, tmp_path: Path) -> None:
        with pytest.raises(LoadError, match="threshold"):
            load(empty_db, self.write(tmp_path / "quote.csv"))


def test_a_field_too_long_rejects_its_row(empty_db: Engine, tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "long.csv",
        {"imdb_title_id": "tt9000201"},
        {"imdb_title_id": "tt9000202", "description": "x" * 2001},
    )
    summary = load(empty_db, path, max_rejected_share=1)
    assert (summary.rows_loaded, summary.rejections) == (1, {"field too long": 1})


def test_invisible_characters_are_removed_and_counted(empty_db: Engine, tmp_path: Path) -> None:
    """A right-to-left override can show a title backwards; a zero-width space breaks the search."""
    path = write_csv(
        tmp_path / "invisible.csv",
        {
            "imdb_title_id": "tt9000301",
            "original_title": "Evil‮ Title",
            "title": "Zero​Width\u0007",
            "director": "Some\tOne",
            "description": "Café⁦ au lait﻿",
        },
    )
    summary = load(empty_db, path, max_rejected_share=1)
    loaded = movie(empty_db, "tt9000301")
    assert (loaded["original_title"], loaded["italian_title"]) == ("Evil Title", "ZeroWidth")
    assert loaded["directors"] == ["Some One"]
    assert loaded["description"] == "Café au lait"
    assert summary.corrections["invisible_characters_removed"] == 4


def test_emoji_and_joiners_are_kept(empty_db: Engine, tmp_path: Path) -> None:
    title = "Family 👨‍👩‍👧 and می‌خواهم"
    load(empty_db, write_csv(tmp_path / "joiners.csv", {"imdb_title_id": "tt9000401", "original_title": title}))
    assert movie(empty_db, "tt9000401")["original_title"] == title


# Garbage made of what usually breaks parsers: quotes, commas, separators, control and invisible characters,
# other scripts, huge and negative numbers, and the null tokens of the CSV.
NASTY = [
    "",
    " ",
    '"',
    '""',
    ",",
    ";",
    "\\",
    "%",
    "_",
    "'; DROP TABLE movies; --",
    "\x00",
    "\x1b[31m",
    "‮",
    "​",
    "﻿",
    "Ã©",
    "None",
    "N/A",
    "null",
    "-1",
    "0",
    "1e309",
    "NaN",
    "9" * 400,
    "$ 9",
    "EUR -5",
    "1994 2001",
    "TV Movie 2019",
    "tt",
    "tt0000000",
    "中文",
    "עברית",
    "👨‍👩",
    "=HYPERLINK()",
]


def garbage(rng: random.Random) -> str:
    parts = [rng.choice(NASTY) if rng.random() < 0.7 else "".join(rng.choices(string.printable, k=rng.randint(1, 12)))]
    while rng.random() < 0.4:
        parts.append(rng.choice(NASTY))
    return rng.choice(["", " ", ", "]).join(parts)


def fuzzed_row(rng: random.Random, base: dict[str, str]) -> dict[str, str]:
    row = dict(base)
    for column in rng.sample(CSV_COLUMNS, k=rng.randint(1, 6)):
        row[column] = garbage(rng)
    return row


def assert_storable(result: dict[str, Any]) -> None:
    """What the CHECK constraints of the table and the API expect of a loaded movie."""
    assert result["imdb_title_id"].startswith("tt")
    assert 1880 <= result["year"] <= 2100
    assert result["genres"]
    assert result["original_title"] and result["italian_title"]
    for value in result.values():
        texts = value if isinstance(value, list) else [value]
        for text in texts:
            if isinstance(text, str):
                assert "\x00" not in text
                assert "‮" not in text


@pytest.mark.parametrize("seed", range(5))
def test_garbage_rows_are_cleaned_or_rejected_never_a_crash(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 (a fixed seed, so a failure can be repeated; nothing secret)
    bases = sample_rows(16)
    outcomes = {"loaded": 0, "rejected": 0}
    for _ in range(2000):
        row = fuzzed_row(rng, rng.choice(bases))
        try:
            result, _ = clean_row(row, max_year=2030)
        except InvalidValue:
            outcomes["rejected"] += 1
            continue
        assert_storable(result)
        outcomes["loaded"] += 1
    # Both paths were exercised.
    assert outcomes["loaded"] and outcomes["rejected"]


@pytest.mark.parametrize("seed", range(3))
def test_a_file_with_garbage_lines_loads_or_stops_cleanly(empty_db: Engine, tmp_path: Path, seed: int) -> None:
    """Random lines among good rows: unbalanced quotes, missing and extra fields. Nothing but LoadError escapes,
    and every line of the file ends up loaded or rejected."""
    rng = random.Random(seed)  # noqa: S311 (a fixed seed, so a failure can be repeated; nothing secret)
    path = write_csv(tmp_path / "base.csv", *({"imdb_title_id": f"tt95{n:05d}"} for n in range(60)))
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    header, body = lines[0], lines[1:]
    for _ in range(15):
        line = ",".join(garbage(rng) for _ in range(rng.randint(1, 30))) + "\r\n"
        body.insert(rng.randrange(len(body) + 1), line)
    path.write_text(header + "".join(body), encoding="utf-8")
    try:
        summary = load(empty_db, path, max_rejected_share=1, force=True)
    except LoadError:
        with empty_db.connect() as conn:
            assert conn.execute(select(func.count()).select_from(movies)).scalar_one() == 0
        return
    assert summary.rows_loaded + summary.rows_rejected == summary.rows_read
    # Every physical line after the header, counted the way the csv module reads them: none is lost.
    with path.open(encoding="utf-8", newline="") as file:
        assert summary.rows_read == sum(1 for _ in file) - 1
