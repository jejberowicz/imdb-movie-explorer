"""Movie routes. They validate the request, call the service and return its model."""

from flask import abort
from flask_openapi3 import APIBlueprint, Tag

from ..errors import Problem
from ..schemas.movies import MovieDetail, MovieListQuery, MoviePage, MoviePath
from ..services import movies as service

movies_bp = APIBlueprint("movies", __name__, url_prefix="/movies", abp_tags=[Tag(name="movies")])


@movies_bp.get("", responses={200: MoviePage, 400: Problem})
def list_movies(query: MovieListQuery):
    """A page of movies, with optional search, filters and order.

    Without parameters: the first 20 movies by weighted rating. With `title`: the movies whose original or
    Italian title contains it, ignoring case and accents, by relevance and popularity.
    """
    return service.list_movies(query).model_dump(mode="json")


@movies_bp.get("/<string:imdb_title_id>", responses={200: MovieDetail, 400: Problem, 404: Problem})
def get_movie(path: MoviePath):
    """Everything about one movie."""
    movie = service.get_movie(path.imdb_title_id)
    if movie is None:
        abort(404, description=f"Movie {path.imdb_title_id} not found.")
    return movie.model_dump(mode="json")
