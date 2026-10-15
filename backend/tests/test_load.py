"""The first load: the whole sample goes in, with folded titles and the weighted rating."""

from sqlalchemy import Engine, func, select

from app.etl.load import load
from app.models import movies
from tests.conftest import SAMPLE_CSV


def count(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(movies)).scalar_one()


def test_the_whole_sample_is_loaded(sample_db: Engine) -> None:
    assert count(sample_db) == 16


def test_titles_are_stored_folded_for_the_search(sample_db: Engine) -> None:
    with sample_db.connect() as conn:
        aeon = conn.execute(select(movies).where(movies.c.imdb_title_id == "tt0402022")).mappings().one()
        amelie = conn.execute(select(movies).where(movies.c.imdb_title_id == "tt0211915")).mappings().one()
    assert aeon["original_title_search"] == "aeon flux"
    assert amelie["italian_title"] == "Il favoloso mondo di Amélie"
    assert amelie["italian_title_search"] == "il favoloso mondo di amelie"


def test_weighted_rating_tops_shawshank_and_sinks_few_votes(sample_db: Engine) -> None:
    with sample_db.connect() as conn:
        top = conn.execute(select(movies.c.imdb_title_id).order_by(movies.c.weighted_rating.desc())).scalars().all()
    assert top[0] == "tt0111161"
    # Suvarna Sundari has the highest raw rating (9.9) but only 896 votes.
    assert top.index("tt7822474") > 5


def test_loading_again_replaces_the_table(sample_db: Engine) -> None:
    load(sample_db, SAMPLE_CSV)
    assert count(sample_db) == 16
