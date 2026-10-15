"""The load against a real PostgreSQL: cleaning rules, rejections, threshold, idempotency and audit."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, func, select

from app.etl.load import LoadError, load
from app.models import load_rejections, load_runs, movies
from tests.conftest import EDGE_CASES_CSV, SAMPLE_CSV

TODAY = date(2026, 10, 15)


def movie(engine: Engine, imdb_title_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        return dict(conn.execute(select(movies).where(movies.c.imdb_title_id == imdb_title_id)).mappings().one())


def count(engine: Engine, table: Any) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(table)).scalar_one()


def load_edge_cases(engine: Engine) -> Any:
    # 5 of 18 rows are invalid on purpose: over the default 1% threshold.
    return load(engine, EDGE_CASES_CSV, max_rejected_share=0.5, today=TODAY)


class TestEdgeCases:
    def test_summary(self, empty_db: Engine) -> None:
        summary = load_edge_cases(empty_db)
        assert (summary.rows_read, summary.rows_loaded, summary.rows_rejected) == (18, 13, 5)
        assert summary.rejections == {
            "malformed imdb_title_id": 1,
            "more than one year": 1,
            "wrong number of fields": 1,
            "empty original_title": 1,
            "duplicate imdb_title_id": 1,
        }
        for code in ("year_from_text", "comma_name_kept", "duplicate_items_removed", "zero_amount_to_null",
                     "dollar_sign_to_usd", "mojibake_repaired", "mojibake_kept", "invalid_metascore_dropped",
                     "whole_from_decimal"):  # fmt: skip
            assert summary.corrections[code] >= 1, code

    def test_year_written_with_text(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        assert movie(empty_db, "tt8206668")["year"] == 2019  # Bad Education, "TV Movie 2019"

    def test_none_is_a_language_without_dialogue(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        assert movie(empty_db, "tt0000009")["languages"] == ["None"]  # Miss Jerry (1894), silent
        assert movie(empty_db, "tt0012349")["languages"] == ["English", "None"]  # The Kid (1921)

    def test_lists(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        assert "Norse, Old" in movie(empty_db, "tt0120657")["languages"]  # The 13th Warrior
        assert movie(empty_db, "tt0099685")["writers"] == ["Nicholas Pileggi"]  # Goodfellas

    def test_money(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        shawshank = movie(empty_db, "tt0111161")
        assert (shawshank["budget_amount"], shawshank["budget_currency"]) == (25000000, "USD")
        deldadeh = movie(empty_db, "tt2351576")
        assert (deldadeh["budget_amount"], deldadeh["budget_currency"]) == (350000000000, "IRR")
        patient_seven = movie(empty_db, "tt5345298")  # "$ 0"
        assert (patient_seven["budget_amount"], patient_seven["budget_currency"]) == (None, None)

    def test_whole_numbers_written_as_decimals(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        shawshank = movie(empty_db, "tt0111161")
        assert (shawshank["metascore"], shawshank["reviews_from_users"]) == (80, 8232)

    def test_invalid_optional_value_is_dropped_but_the_movie_stays(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        assert movie(empty_db, "tt9000004")["metascore"] is None  # "57.5"

    def test_mojibake(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        assert "tío de Carlos" in movie(empty_db, "tt0291942")["description"]  # Gente pez, repaired
        assert "Ã" in movie(empty_db, "tt1262941")["description"]  # Pickin' & Grinnin', irreversible: as is

    def test_titles_that_look_like_nulls_are_real(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        assert movie(empty_db, "tt0450340")["original_title"] == "Unknown"
        assert movie(empty_db, "tt0775413")["original_title"] == "?"


class TestRejections:
    def test_rejected_rows_are_kept_with_reason_and_original_content(self, empty_db: Engine) -> None:
        load_edge_cases(empty_db)
        with empty_db.connect() as conn:
            rows = conn.execute(select(load_rejections).order_by(load_rejections.c.line_number)).mappings().all()
        assert [(row["line_number"], row["reason"]) for row in rows] == [
            (14, "malformed imdb_title_id"),
            (15, "more than one year"),
            (16, "wrong number of fields"),
            (17, "empty original_title"),
            (19, "duplicate imdb_title_id"),
        ]
        assert rows[1]["raw"]["year"] == "1999 2001"
        assert rows[2]["raw"]["_extra_fields"] == ["extra"]

    def test_too_many_rejections_cancel_the_load_without_touching_the_data(self, empty_db: Engine) -> None:
        load(empty_db, SAMPLE_CSV)
        with pytest.raises(LoadError, match="over the 1% threshold"):
            load(empty_db, EDGE_CASES_CSV, today=TODAY)
        assert count(empty_db, movies) == 16
        assert count(empty_db, load_runs) == 1

    def test_missing_columns(self, empty_db: Engine, tmp_path: Path) -> None:
        broken = tmp_path / "broken.csv"
        broken.write_text("imdb_title_id,title\ntt0111161,Le ali della libertà\n", encoding="utf-8")
        with pytest.raises(LoadError, match="missing columns"):
            load(empty_db, broken)


class TestIdempotency:
    def test_the_same_file_is_not_loaded_twice(self, empty_db: Engine) -> None:
        assert not load(empty_db, SAMPLE_CSV).skipped
        assert load(empty_db, SAMPLE_CSV).skipped
        assert count(empty_db, load_runs) == 1
        assert count(empty_db, movies) == 16

    def test_force_loads_again_with_the_same_result(self, empty_db: Engine) -> None:
        load(empty_db, SAMPLE_CSV)
        load(empty_db, SAMPLE_CSV, force=True)
        assert count(empty_db, load_runs) == 2
        assert count(empty_db, movies) == 16

    def test_another_file_replaces_the_movies(self, empty_db: Engine) -> None:
        load(empty_db, SAMPLE_CSV)
        load_edge_cases(empty_db)
        assert count(empty_db, movies) == 13


class TestAudit:
    def test_the_load_is_recorded(self, empty_db: Engine) -> None:
        summary = load(empty_db, SAMPLE_CSV)
        with empty_db.connect() as conn:
            run = conn.execute(select(load_runs)).mappings().one()
        assert run["source"] == "movies_sample.csv"
        assert run["sha256"] == summary.sha256
        assert (run["rows_read"], run["rows_loaded"], run["rows_rejected"]) == (16, 16, 0)
        assert run["corrections"]["dollar_sign_to_usd"] >= 1
        assert run["mean_vote"] == pytest.approx(summary.mean_vote)

    def test_weighted_rating_tops_shawshank_and_sinks_few_votes(self, empty_db: Engine) -> None:
        load(empty_db, SAMPLE_CSV)
        with empty_db.connect() as conn:
            ranking = (
                conn.execute(select(movies.c.imdb_title_id).order_by(movies.c.weighted_rating.desc())).scalars().all()
            )
        assert ranking[0] == "tt0111161"
        # Suvarna Sundari has the highest raw rating (9.9) but only 896 votes.
        assert ranking.index("tt7822474") > 5

    def test_titles_are_stored_folded_for_the_search(self, empty_db: Engine) -> None:
        load(empty_db, SAMPLE_CSV)
        assert movie(empty_db, "tt0402022")["original_title_search"] == "aeon flux"
        assert movie(empty_db, "tt0211915")["italian_title_search"] == "il favoloso mondo di amelie"
