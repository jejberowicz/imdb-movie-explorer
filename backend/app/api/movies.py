"""Movie routes. They validate the request, call the service and return its model."""

from flask_openapi3 import APIBlueprint, Tag

from ..schemas.movies import MovieListQuery, MoviePage
from ..services import movies as service

movies_bp = APIBlueprint("movies", __name__, url_prefix="/movies", abp_tags=[Tag(name="movies")])


@movies_bp.get("", responses={200: MoviePage})
def list_movies(query: MovieListQuery):
    """A page of movies; with `title`, only those whose title contains it."""
    return service.list_movies(query).model_dump(mode="json")
