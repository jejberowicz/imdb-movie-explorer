"""Acceptance criteria, against the whole CSV: the 85.855 movies are loaded once for this module.

They take a few seconds more than the rest; `pytest -m "not acceptance"` leaves them out.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from sqlalchemy import Engine

from app import create_app
from app.config import Settings
from app.etl.load import load

pytestmark = pytest.mark.acceptance
FULL_CSV = Path(__file__).resolve().parents[2] / "data" / "IMDb_movies.csv.gz"


@pytest.fixture(scope="module")
def full(engine: Engine, database_url: str) -> Iterator[FlaskClient]:
    summary = load(engine, FULL_CSV, force=True)
    assert (summary.rows_loaded, summary.rows_rejected) == (85855, 0)
    yield create_app(Settings(database_url=database_url)).test_client()


def ids(response) -> list[str]:
    return [movie["imdb_title_id"] for movie in response.get_json()["items"]]


def test_list_has_every_movie(full: FlaskClient) -> None:
    response = full.get("/movies")
    assert response.status_code == 200
    body = response.get_json()
    assert (body["total"], body["page_size"], len(body["items"])) == (85855, 20, 20)


def test_shawshank_first(full: FlaskClient) -> None:
    assert ids(full.get("/movies?title=shawshank"))[0] == "tt0111161"


def test_godfather_then_part_two(full: FlaskClient) -> None:
    assert ids(full.get("/movies?title=godfather"))[:2] == ["tt0068646", "tt0071562"]


def test_relatos_salvajes_although_the_csv_title_is_italian(full: FlaskClient) -> None:
    assert ids(full.get("/movies?title=relatos salvajes")) == ["tt3011894"]


def test_amelie_without_the_accent(full: FlaskClient) -> None:
    assert "tt0211915" in ids(full.get("/movies?title=amelie"))


def test_wildcards_only_match_themselves(full: FlaskClient) -> None:
    assert full.get("/movies?title=%25").get_json()["total"] == 10
    assert full.get("/movies?title=_").get_json()["total"] == 7


def test_empty_title_and_too_long_title(full: FlaskClient) -> None:
    assert full.get("/movies?title=").get_json()["total"] == 85855
    assert full.get("/movies?title=" + "x" * 201).status_code == 400


@pytest.mark.parametrize("query", ["page_size=100000", "page=0", "page=abc"])
def test_invalid_pagination(full: FlaskClient, query: str) -> None:
    assert full.get(f"/movies?{query}").status_code == 400


def test_sort_injection_is_rejected_and_the_table_survives(full: FlaskClient) -> None:
    assert full.get("/movies?sort=title;DROP TABLE movies").status_code == 400
    assert full.get("/movies").get_json()["total"] == 85855


def test_weighted_rating_tops_the_classics_and_not_few_votes(full: FlaskClient) -> None:
    top = ids(full.get("/movies?page_size=100"))
    assert top[:2] == ["tt0111161", "tt0068646"]
    assert "tt7822474" not in top  # Suvarna Sundari: 9.9 with 896 votes


def test_detail(full: FlaskClient) -> None:
    assert full.get("/movies/tt0068646").get_json()["original_title"] == "The Godfather"
    assert full.get("/movies/tt9999999").status_code == 404
    assert full.get("/movies/tt0068646x").status_code == 400


def test_letters_that_nfkd_does_not_fold(full: FlaskClient) -> None:
    assert "tt0402022" in ids(full.get("/movies?title=aeon flux"))


def test_dollars_are_usd(full: FlaskClient) -> None:
    assert full.get("/movies/tt0111161").get_json()["budget"] == {"amount": 25000000, "currency": "USD"}


def test_every_country_has_a_map_code(full: FlaskClient) -> None:
    countries = full.get("/countries").get_json()["items"]
    assert len(countries) == 194
    assert all(country["map_code"] for country in countries)
    assert sum(country["former"] for country in countries) == 13


def test_russia_with_the_soviet_union(full: FlaskClient) -> None:
    assert full.get("/movies?country=Russia&country=Soviet Union").get_json()["total"] == 1947
