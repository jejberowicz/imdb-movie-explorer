"""GET /movies against the sample: pagination, search in both titles, folding and wildcards."""

from flask.testing import FlaskClient


def ids(response) -> list[str]:
    return [movie["imdb_title_id"] for movie in response.get_json()["items"]]


def test_health(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_list_is_paginated_and_ordered_by_weighted_rating(client: FlaskClient) -> None:
    body = client.get("/movies?page_size=5").get_json()
    assert body["total"] == 16
    assert body["total_pages"] == 4
    assert len(body["items"]) == 5
    assert body["items"][0]["original_title"] == "The Shawshank Redemption"
    assert set(body["items"][0]) == {
        "imdb_title_id",
        "original_title",
        "year",
        "genres",
        "directors",
        "duration",
        "avg_vote",
        "votes",
        "weighted_rating",
    }


def test_page_past_the_end_keeps_the_total(client: FlaskClient) -> None:
    body = client.get("/movies?page=99").get_json()
    assert body["items"] == []
    assert body["total"] == 16


def test_search_uses_the_original_title(client: FlaskClient) -> None:
    assert ids(client.get("/movies?title=shawshank")) == ["tt0111161"]
    # The CSV `title` says "Storie Pazzesche": only the original title has it.
    assert ids(client.get("/movies?title=relatos salvajes")) == ["tt3011894"]


def test_search_also_uses_the_italian_title(client: FlaskClient) -> None:
    assert ids(client.get("/movies?title=padrino")) == ["tt0068646", "tt0071562", "tt0099674"]


def test_search_orders_by_relevance_then_votes(client: FlaskClient) -> None:
    assert ids(client.get("/movies?title=godfather")) == ["tt0068646", "tt0071562", "tt0099674"]


def test_search_ignores_case_and_accents(client: FlaskClient) -> None:
    assert "tt0211915" in ids(client.get("/movies?title=AMELIE"))
    assert ids(client.get("/movies?title=aeon flux")) == ["tt0402022"]


def test_search_takes_wildcards_literally(client: FlaskClient) -> None:
    assert set(ids(client.get("/movies?title=%"))) == {"tt0884819", "tt0485366"}
    assert set(ids(client.get("/movies?title=_"))) == {"tt0291141", "tt0302889"}


def test_blank_title_means_no_filter(client: FlaskClient) -> None:
    assert client.get("/movies?title=%20%20").get_json()["total"] == 16


def test_invalid_parameters_are_400(client: FlaskClient) -> None:
    assert client.get("/movies?page=0").status_code == 400
    assert client.get("/movies?page=abc").status_code == 400
    assert client.get("/movies?page_size=101").status_code == 400
    assert client.get("/movies?title=" + "x" * 201).status_code == 400
