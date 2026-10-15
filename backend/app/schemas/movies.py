"""Request and response models of the movies endpoints. Pydantic validates and documents them."""

from pydantic import BaseModel, Field, field_serializer, field_validator


class MovieListQuery(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Text anywhere in the original or the Italian title, ignoring case and accents.",
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("title")
    @classmethod
    def blank_means_no_filter(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None


class MovieSummary(BaseModel):
    imdb_title_id: str
    original_title: str
    year: int
    genres: list[str]
    directors: list[str]
    duration: int
    avg_vote: float
    votes: int
    weighted_rating: float

    @field_serializer("weighted_rating")
    def two_decimals(self, value: float) -> float:
        # The order uses the exact value in the database; two decimals are enough to show it.
        return round(value, 2)


class MoviePage(BaseModel):
    items: list[MovieSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
