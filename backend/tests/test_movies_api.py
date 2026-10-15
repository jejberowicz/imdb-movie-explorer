"""The API against the sample of 16 movies: list, search, filters, order, detail, catalog, health and errors."""

import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from sqlalchemy import Connection, Engine, text

from app import create_app
from app.config import Settings
from app.etl.load import load
from app.text import fold
from tests.test_load import write_csv


def ids(response) -> list[str]:
    return ids_of(response.get_json())


def ids_of(body: dict) -> list[str]:
    return [movie["imdb_title_id"] for movie in body["items"]]


class TestList:
    def test_paginated_and_ordered_by_weighted_rating(self, client: FlaskClient) -> None:
        body = client.get("/movies?page_size=5").get_json()
        assert (body["total"], body["total_pages"], len(body["items"])) == (16, 4, 5)
        assert body["items"][0]["original_title"] == "The Shawshank Redemption"
        assert list(body["items"][0]) == [
            "imdb_title_id",
            "original_title",
            "year",
            "genres",
            "directors",
            "countries",
            "duration",
            "avg_vote",
            "votes",
            "weighted_rating",
        ]

    def test_weighted_rating_has_two_decimals(self, client: FlaskClient) -> None:
        rating = client.get("/movies?page_size=1").get_json()["items"][0]["weighted_rating"]
        assert rating == round(rating, 2)

    def test_pages_do_not_repeat_movies(self, client: FlaskClient) -> None:
        pages = [ids(client.get(f"/movies?page_size=3&page={page}")) for page in range(1, 7)]
        seen = [movie for page in pages for movie in page]
        assert len(seen) == len(set(seen)) == 16

    def test_page_past_the_end_keeps_the_total(self, client: FlaskClient) -> None:
        body = client.get("/movies?page=99").get_json()
        assert (body["items"], body["total"]) == ([], 16)

    def test_unknown_parameters_are_ignored(self, client: FlaskClient) -> None:
        assert client.get("/movies?foo=bar").status_code == 200


class TestSearch:
    def test_original_title(self, client: FlaskClient) -> None:
        assert ids(client.get("/movies?title=shawshank")) == ["tt0111161"]
        # The CSV `title` says "Storie Pazzesche": only the original title has it.
        assert ids(client.get("/movies?title=relatos salvajes")) == ["tt3011894"]

    def test_italian_title(self, client: FlaskClient) -> None:
        assert ids(client.get("/movies?title=padrino")) == ["tt0068646", "tt0071562", "tt0099674"]

    def test_relevance_then_popularity(self, client: FlaskClient) -> None:
        assert ids(client.get("/movies?title=godfather")) == ["tt0068646", "tt0071562", "tt0099674"]

    def test_case_and_accents(self, client: FlaskClient) -> None:
        assert "tt0211915" in ids(client.get("/movies?title=AMELIE"))
        assert ids(client.get("/movies?title=aeon flux")) == ["tt0402022"]

    def test_wildcards_are_literal(self, client: FlaskClient) -> None:
        assert set(ids(client.get("/movies?title=%"))) == {"tt0884819", "tt0485366"}
        assert set(ids(client.get("/movies?title=_"))) == {"tt0291141", "tt0302889"}

    def test_blank_title_means_no_filter(self, client: FlaskClient) -> None:
        assert client.get("/movies?title=%20%20").get_json()["total"] == 16

    def test_title_without_letters_after_folding_means_no_filter(self, client: FlaskClient) -> None:
        """A lone combining accent folds to "": as a search it matched every movie with the slowest query."""
        assert ids(client.get("/movies?title=%CC%81%CC%81&page_size=100")) == ids(client.get("/movies?page_size=100"))
        assert client.get("/movies?title=%CC%81&sort=relevance").status_code == 400

    def test_search_can_be_sorted_by_another_field(self, client: FlaskClient) -> None:
        assert ids(client.get("/movies?title=godfather&sort=year&order=asc")) == ["tt0068646", "tt0071562", "tt0099674"]


class TestFiltersAndOrder:
    def test_genre(self, client: FlaskClient) -> None:
        body = client.get("/movies?genre=Crime").get_json()
        assert body["total"] == 5  # the three Godfathers, Pulp Fiction and The Dark Knight
        assert all("Crime" in movie["genres"] for movie in body["items"])

    def test_unknown_genre_is_an_empty_list(self, client: FlaskClient) -> None:
        assert client.get("/movies?genre=Nope").get_json()["total"] == 0

    def test_genre_can_repeat_and_matches_all(self, client: FlaskClient) -> None:
        """Crime and Drama are the crime dramas, not every crime movie and every drama."""
        crime = set(ids(client.get("/movies?genre=Crime")))
        body = client.get("/movies?genre=Crime&genre=Drama").get_json()
        assert body["total"] > 0
        assert all({"Crime", "Drama"} <= set(movie["genres"]) for movie in body["items"])
        assert set(ids_of(body)) <= crime

    def test_decade_can_repeat_and_matches_any(self, client: FlaskClient) -> None:
        nineties = client.get("/movies?decade=1990").get_json()
        assert nineties["total"] and all(1990 <= movie["year"] <= 1999 for movie in nineties["items"])
        both = client.get("/movies?decade=1970&decade=1990&page_size=100").get_json()
        assert {movie["year"] // 10 * 10 for movie in both["items"]} == {1970, 1990}
        assert both["total"] > nineties["total"]

    def test_a_year_inside_a_decade(self, client: FlaskClient) -> None:
        body = client.get("/movies?decade=1990&year_from=1994&year_to=1994").get_json()
        years = [movie["year"] for movie in body["items"]]
        assert years and set(years) == {1994}

    def test_year_range(self, client: FlaskClient) -> None:
        years = [movie["year"] for movie in client.get("/movies?year_from=1990&year_to=1999").get_json()["items"]]
        assert years and all(1990 <= year <= 1999 for year in years)

    def test_min_votes(self, client: FlaskClient) -> None:
        votes = [movie["votes"] for movie in client.get("/movies?min_votes=1000000").get_json()["items"]]
        assert votes and min(votes) >= 1_000_000

    def test_country_can_repeat_and_matches_any(self, client: FlaskClient) -> None:
        argentina = set(ids(client.get("/movies?country=Argentina")))
        both = set(ids(client.get("/movies?country=Argentina&country=India")))
        assert "tt3011894" in argentina
        assert argentina < both

    @pytest.mark.parametrize(
        ("query", "key", "reverse"),
        [
            ("sort=votes", "votes", True),
            ("sort=year&order=asc", "year", False),
            ("sort=duration", "duration", True),
            ("sort=title", "original_title", False),
        ],
    )
    def test_sort(self, client: FlaskClient, query: str, key: str, reverse: bool) -> None:
        values = [movie[key] for movie in client.get(f"/movies?{query}&page_size=100").get_json()["items"]]
        if key == "original_title":
            values = [fold(value) for value in values]
        assert values == sorted(values, reverse=reverse)


class TestAlphabeticalOrder:
    TITLES = ("Zodiac", "#Alive", "$", "Amélie", "(500) Days of Summer", "¡Three Amigos!", "'71")

    @pytest.fixture
    def titles_client(self, empty_db: Engine, database_url: str, tmp_path: Path) -> FlaskClient:
        rows = ({"imdb_title_id": f"tt90007{n:02d}", "original_title": title} for n, title in enumerate(self.TITLES))
        load(empty_db, write_csv(tmp_path / "titles.csv", *rows))
        app = create_app(Settings(database_url=database_url))
        app.config["TESTING"] = True
        return app.test_client()

    def titles(self, client: FlaskClient, order: str) -> list[str]:
        items = client.get(f"/movies?sort=title&order={order}").get_json()["items"]
        return [movie["original_title"] for movie in items]

    def test_the_symbols_at_the_start_are_skipped(self, titles_client: FlaskClient) -> None:
        """«#Alive» goes with the A, not before every letter; a title of symbols only goes last."""
        assert self.titles(titles_client, "asc") == [
            "(500) Days of Summer",
            "'71",
            "#Alive",
            "Amélie",
            "¡Three Amigos!",
            "Zodiac",
            "$",
        ]

    def test_a_title_of_symbols_only_is_last_either_way(self, titles_client: FlaskClient) -> None:
        assert self.titles(titles_client, "desc") == [
            "Zodiac",
            "¡Three Amigos!",
            "Amélie",
            "#Alive",
            "'71",
            "(500) Days of Summer",
            "$",
        ]


class TestValidation:
    @pytest.mark.parametrize(
        ("query", "parameter"),
        [
            ("page=0", "page"),
            ("page=abc", "page"),
            ("page_size=0", "page_size"),
            ("page_size=100000", "page_size"),
            ("title=" + "x" * 201, "title"),
            ("sort=title;DROP TABLE movies", "sort"),
            ("order=sideways", "order"),
            ("year_from=1700", "year_from"),
            ("min_votes=-1", "min_votes"),
            ("country=" + "x" * 61, "country.0"),
            # A NUL byte reached PostgreSQL, which rejects it: it was a 500.
            ("title=god%00father", "title"),
            ("genre=Dr%00ama", "genre.0"),
            ("country=USA&country=It%00aly", "country.1"),
            ("genre=Crime&genre=Dr%00ama", "genre.1"),
            ("&".join(["genre=Drama"] * 11), "genre"),
            ("decade=1995", "decade.0"),
            ("decade=1990&decade=1870", "decade.1"),
            ("decade=abc", "decade.0"),
        ],
    )
    def test_invalid_parameter_is_a_400_problem(self, client: FlaskClient, query: str, parameter: str) -> None:
        response = client.get(f"/movies?{query}")
        assert response.status_code == 400
        assert response.mimetype == "application/problem+json"
        body = response.get_json()
        assert (body["type"], body["title"], body["status"]) == ("about:blank", "Bad Request", 400)
        assert parameter in [error["parameter"] for error in body["errors"]]

    def test_cross_field_rules(self, client: FlaskClient) -> None:
        assert client.get("/movies?year_from=2000&year_to=1990").status_code == 400
        assert client.get("/movies?sort=relevance").status_code == 400

    def test_injection_in_sort_leaves_the_table_intact(self, client: FlaskClient) -> None:
        assert client.get("/movies?sort=title;DROP TABLE movies").status_code == 400
        assert client.get("/movies").get_json()["total"] == 16


class TestDetail:
    def test_everything_about_a_movie(self, client: FlaskClient) -> None:
        movie = client.get("/movies/tt0111161").get_json()
        assert movie["original_title"] == "The Shawshank Redemption"
        assert movie["italian_title"] == "Le ali della libertà"
        assert movie["budget"] == {"amount": 25000000, "currency": "USD"}
        assert movie["worldwide_gross_income"] == {"amount": 28815245, "currency": "USD"}
        assert movie["metascore"] == 80
        assert movie["imdb_url"] == "https://www.imdb.com/title/tt0111161/"
        assert "date_published" not in movie

    def test_missing_data_is_null(self, client: FlaskClient) -> None:
        movie = client.get("/movies/tt7822474").get_json()  # Suvarna Sundari: no budget, no metascore
        assert movie["budget"] is None
        assert movie["metascore"] is None

    def test_unknown_id_is_404(self, client: FlaskClient) -> None:
        response = client.get("/movies/tt9999999")
        assert response.status_code == 404
        assert response.get_json() == {
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": "Movie tt9999999 not found.",
        }

    def test_malformed_id_is_400(self, client: FlaskClient) -> None:
        assert client.get("/movies/abc").status_code == 400


class TestCatalog:
    def test_genres(self, client: FlaskClient) -> None:
        response = client.get("/genres")
        assert response.headers["Cache-Control"] == "public, max-age=3600"
        items = response.get_json()["items"]
        assert items[0] == {"name": "Drama", "movies": 9}
        assert [item["movies"] for item in items] == sorted((item["movies"] for item in items), reverse=True)

    def test_countries(self, client: FlaskClient) -> None:
        response = client.get("/countries")
        assert response.headers["Cache-Control"] == "public, max-age=3600"
        items = {item["name"]: item for item in response.get_json()["items"]}
        assert items["USA"] == {"name": "USA", "movies": 10, "map_code": "US", "former": False}
        assert items["Argentina"]["map_code"] == "AR"

    def test_years(self, client: FlaskClient) -> None:
        response = client.get("/years")
        assert response.headers["Cache-Control"] == "public, max-age=3600"
        items = response.get_json()["items"]
        years = [item["year"] for item in items]
        assert years == sorted(set(years))
        assert sum(item["movies"] for item in items) == 16


class TestHealth:
    def test_liveness(self, client: FlaskClient) -> None:
        assert client.get("/health").get_json() == {"status": "ok"}

    def test_ready_with_data(self, client: FlaskClient) -> None:
        assert client.get("/health/ready").get_json() == {"status": "ready", "movies": 16}

    def test_not_ready_without_data(self, empty_db: Engine, database_url: str) -> None:
        client = create_app(Settings(database_url=database_url)).test_client()
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.get_json()["detail"] == "No movies loaded yet."

    def test_not_ready_without_database(self) -> None:
        url = "postgresql+psycopg://nobody:wrong@127.0.0.1:9/nothing"
        client = create_app(Settings(database_url=url)).test_client()
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.get_json()["detail"] == "The database is not available."


class TestErrors:
    def test_unknown_route_is_a_404_problem(self, client: FlaskClient) -> None:
        response = client.get("/nope")
        assert response.status_code == 404
        assert response.mimetype == "application/problem+json"

    def test_wrong_method_is_a_405_problem(self, client: FlaskClient) -> None:
        response = client.post("/movies")
        assert response.status_code == 405
        assert response.get_json()["title"] == "Method Not Allowed"
        # RFC 9110: a 405 says which methods the resource does accept.
        assert set(response.headers["Allow"].split(", ")) >= {"GET", "HEAD"}
        assert response.mimetype == "application/problem+json"

    def test_unexpected_errors_never_show_internals(self, client: FlaskClient, monkeypatch) -> None:
        def boom(*args, **kwargs):
            raise RuntimeError("secret internals")

        monkeypatch.setattr("app.services.movies.list_movies", boom)
        response = client.get("/movies")
        assert response.status_code == 500
        assert "secret" not in response.get_data(as_text=True)
        assert response.get_json()["detail"] == "Unexpected error."


class TestDatabaseErrors:
    """The database down or too slow is a 503 with one log line, not a 500 with a traceback per request."""

    def test_database_down_is_a_503(self, caplog: pytest.LogCaptureFixture) -> None:
        client = create_app(
            Settings(database_url="postgresql+psycopg://nobody:wrong@127.0.0.1:9/nothing")
        ).test_client()
        response = client.get("/movies")
        assert response.status_code == 503
        assert response.mimetype == "application/problem+json"
        assert response.get_json()["detail"] == "The database is not available."
        [record] = [record for record in caplog.records if record.name == "app.errors"]
        assert record.exc_info is None
        assert "\n" not in record.getMessage()

    def test_a_query_over_the_statement_timeout_is_a_503(self, client: FlaskClient, monkeypatch) -> None:
        def slow(conn: Connection, *args, **kwargs):
            conn.execute(text("SET LOCAL statement_timeout = '50ms'"))
            conn.execute(text("SELECT pg_sleep(1)"))

        monkeypatch.setattr("app.repositories.movies.find_movies", slow)
        assert client.get("/movies").status_code == 503

    def test_a_database_that_never_answers_times_out(self, monkeypatch) -> None:
        """Without connect_timeout, libpq waits forever and the request ties up a worker until Gunicorn kills it."""
        monkeypatch.setattr("app.db.CONNECT_TIMEOUT", 2, raising=False)  # the minimum of libpq
        silent = socket.socket()
        silent.bind(("127.0.0.1", 0))
        silent.listen()  # the kernel accepts the connection, nobody answers
        url = f"postgresql+psycopg://a:b@127.0.0.1:{silent.getsockname()[1]}/c"
        pool = ThreadPoolExecutor(1)
        try:
            client = create_app(Settings(database_url=url)).test_client()
            response = pool.submit(client.get, "/movies").result(timeout=10)
        finally:
            silent.close()  # a connection still waiting gets a reset, so the thread ends
            pool.shutdown()
        assert response.status_code == 503
