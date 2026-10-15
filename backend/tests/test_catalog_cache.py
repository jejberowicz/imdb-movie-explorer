"""Genres and countries are counted once per load: a new load must show up right away."""

from flask.testing import FlaskClient
from sqlalchemy import Engine, text

from app.etl.load import load
from tests.conftest import EDGE_CASES_CSV


def test_genres_and_countries_follow_a_new_load(client: FlaskClient, sample_db: Engine) -> None:
    before = (client.get("/genres").get_json(), client.get("/countries").get_json())
    assert (client.get("/genres").get_json(), client.get("/countries").get_json()) == before

    load(sample_db, EDGE_CASES_CSV, max_rejected_share=1)

    after = (client.get("/genres").get_json(), client.get("/countries").get_json())
    assert after[0] != before[0]
    assert after[1] != before[1]


def test_an_emptied_database_is_not_answered_from_the_cache(client: FlaskClient, sample_db: Engine) -> None:
    assert client.get("/genres").get_json()["items"]
    with sample_db.begin() as conn:
        conn.execute(text("TRUNCATE movies, load_runs, load_rejections"))
    assert client.get("/genres").get_json() == {"items": []}
