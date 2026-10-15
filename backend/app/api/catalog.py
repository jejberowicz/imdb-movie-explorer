"""Genres and countries, to build the filters and the map. They only change with a new load, so they are cached."""

from flask_openapi3 import APIBlueprint, Tag

from ..schemas.movies import CountryList, GenreList
from ..services import movies as service

catalog_bp = APIBlueprint("catalog", __name__, abp_tags=[Tag(name="catalog")])
CACHE = {"Cache-Control": "public, max-age=3600"}


@catalog_bp.get("/genres", responses={200: GenreList})
def list_genres():
    """The genres, with their number of movies, most frequent first."""
    return service.list_genres().model_dump(mode="json"), 200, CACHE


@catalog_bp.get("/countries", responses={200: CountryList})
def list_countries():
    """The countries as they come in the CSV, with their movies and the country where the map paints them."""
    return service.list_countries().model_dump(mode="json"), 200, CACHE
