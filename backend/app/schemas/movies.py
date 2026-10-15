"""Request and response models. Pydantic validates the requests and the same models document the API."""

import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)

from ..text import fold

CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def no_control_characters(value: str) -> str:
    """No title, genre or country has them, and PostgreSQL rejects a NUL: without this, «%00» would be a 500."""
    if CONTROL_CHARACTERS.search(value):
        raise ValueError("must not contain control characters")
    return value


Text = Annotated[str, AfterValidator(no_control_characters)]
SortField = Literal["relevance", "rating", "year", "votes", "duration", "title"]
CountryName = Annotated[Text, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
GenreName = Annotated[Text, StringConstraints(min_length=1, max_length=40)]
Decade = Annotated[int, Field(ge=1880, le=2100, multiple_of=10)]
Year = Annotated[int, Field(ge=1880, le=2100)]


class MovieListQuery(BaseModel):
    # Unknown parameters are ignored (ADR 0007).
    model_config = ConfigDict(extra="ignore")

    title: Text | None = Field(
        default=None,
        max_length=200,
        description="Text anywhere in the original or the Italian title, ignoring case and accents.",
    )
    page: int = Field(default=1, ge=1, le=100_000)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: SortField | None = Field(
        default=None, description="Default: relevance with a title, the weighted rating without one."
    )
    order: Literal["asc", "desc"] | None = Field(default=None, description="Default: asc for title, desc otherwise.")
    genre: list[GenreName] = Field(
        default_factory=list,
        max_length=10,
        description="A genre of GET /genres; repeat it to get the movies that have all of them.",
    )
    country: list[CountryName] = Field(
        default_factory=list,
        max_length=20,
        description="A country of GET /countries; repeat it to get the movies of any of them.",
    )
    decade: list[Decade] = Field(
        default_factory=list,
        max_length=23,
        description="The first year of a decade (1990 for the 1990s); repeat it to get the movies of any of them.",
    )
    year: list[Year] = Field(
        default_factory=list,
        max_length=50,
        description="A year; repeat it to get the movies of any of them.",
    )
    year_from: int | None = Field(default=None, ge=1880, le=2100)
    year_to: int | None = Field(default=None, ge=1880, le=2100)
    min_votes: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @field_validator("title")
    @classmethod
    def blank_means_no_filter(cls, value: str | None) -> str | None:
        # Blank once folded, as the search compares it: only spaces, or only accents with no letter («%CC%81»).
        # Searching "" would match the whole catalog with the slowest query.
        return value.strip() if value is not None and fold(value) else None

    @model_validator(mode="after")
    def consistent(self) -> "MovieListQuery":
        if self.year_from is not None and self.year_to is not None and self.year_from > self.year_to:
            raise ValueError("year_from must not be greater than year_to")
        if self.sort == "relevance" and not self.title:
            raise ValueError("sort=relevance needs a title to search")
        return self


class MoviePath(BaseModel):
    imdb_title_id: str = Field(pattern=r"^tt[0-9]{7,8}$", description="IMDb id: tt followed by 7 or 8 digits.")


def _two_decimals(value: float) -> float:
    # The order uses the exact value in the database; two decimals are enough to show it.
    return round(value, 2)


class MovieSummary(BaseModel):
    imdb_title_id: str
    original_title: str
    year: int
    genres: list[str]
    directors: list[str] | None
    countries: list[str] | None
    duration: int
    avg_vote: float
    votes: int
    weighted_rating: float

    @field_serializer("weighted_rating")
    def round_rating(self, value: float) -> float:
        return _two_decimals(value)


class MoviePage(BaseModel):
    items: list[MovieSummary]
    page: int
    page_size: int
    total: int
    total_pages: int


class Money(BaseModel):
    amount: int
    currency: str = Field(description="ISO 4217 code: the CSV's $ is published as USD.")


class MovieDetail(BaseModel):
    imdb_title_id: str
    original_title: str
    italian_title: str = Field(description="The `title` column of the CSV, which is in Italian.")
    year: int
    genres: list[str]
    duration: int
    countries: list[str] | None
    languages: list[str] | None = Field(description='"None" means a movie without dialogue.')
    directors: list[str] | None
    writers: list[str] | None
    production_company: str | None
    actors: list[str] | None
    description: str | None
    avg_vote: float
    votes: int
    weighted_rating: float
    metascore: int | None
    reviews_from_users: int | None
    reviews_from_critics: int | None
    budget: Money | None
    usa_gross_income: Money | None
    worldwide_gross_income: Money | None
    imdb_url: str

    @field_serializer("weighted_rating")
    def round_rating(self, value: float) -> float:
        return _two_decimals(value)


class GenreCount(BaseModel):
    name: str
    movies: int


class GenreList(BaseModel):
    items: list[GenreCount]


class CountryCount(BaseModel):
    name: str = Field(description="As it comes in the CSV.")
    movies: int
    map_code: str | None = Field(description="ISO 3166 code of the country where the map paints it.")
    former: bool = Field(description="The country no longer exists: dissolved or renamed (ADR 0009).")


class CountryList(BaseModel):
    items: list[CountryCount]


class YearCount(BaseModel):
    year: int
    movies: int


class YearList(BaseModel):
    items: list[YearCount]
