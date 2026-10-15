"""The API against the sample of 16 movies: list, search, filters, order, detail, catalog, health and errors."""

import pytest
from flask.testing import FlaskClient
from sqlalchemy import Engine

from app import create_app
from app.config import Settings
from app.text import fold


def ids(response) -> list[str]:
    return [movie["imdb_title_id"] for movie in response.get_json()["items"]]


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

    def test_search_can_be_sorted_by_another_field(self, client: FlaskClient) -> None:
        assert ids(client.get("/movies?title=godfather&sort=year&order=asc")) == ["tt0068646", "tt0071562", "tt0099674"]


class TestFiltersAndOrder:
    def test_genre(self, client: FlaskClient) -> None:
        body = client.get("/movies?genre=Crime").get_json()
        assert body["total"] == 5  # the three Godfathers, Pulp Fiction and The Dark Knight
        assert all("Crime" in movie["genres"] for movie in body["items"])

    def test_unknown_genre_is_an_empty_list(self, client: FlaskClient) -> None:
        assert client.get("/movies?genre=Nope").get_json()["total"] == 0

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
            ("genre=Dr%00ama", "genre"),
            ("country=USA&country=It%00aly", "country.1"),
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

    def test_unexpected_errors_never_show_internals(self, client: FlaskClient, monkeypatch) -> None:
        def boom(*args, **kwargs):
            raise RuntimeError("secret internals")

        monkeypatch.setattr("app.services.movies.list_movies", boom)
        response = client.get("/movies")
        assert response.status_code == 500
        assert "secret" not in response.get_data(as_text=True)
        assert response.get_json()["detail"] == "Unexpected error."
