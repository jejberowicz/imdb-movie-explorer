"""Database tables, described with SQLAlchemy Core. The Alembic migrations create them."""

from sqlalchemy import Column, Double, Integer, MetaData, Numeric, SmallInteger, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY

metadata = MetaData()

movies = Table(
    "movies",
    metadata,
    Column("imdb_title_id", Text, primary_key=True),
    Column("original_title", Text, nullable=False),
    # The CSV column `title`, which is in Italian (ADR 0002)
    Column("italian_title", Text, nullable=False),
    # Folded copies for the search: lowercase, without accents (app.text.fold)
    Column("original_title_search", Text, nullable=False),
    Column("italian_title_search", Text, nullable=False),
    Column("year", SmallInteger, nullable=False),
    Column("genres", ARRAY(Text), nullable=False),
    Column("directors", ARRAY(Text)),
    Column("duration", SmallInteger, nullable=False),
    Column("avg_vote", Numeric(3, 1), nullable=False),
    Column("votes", Integer, nullable=False),
    Column("weighted_rating", Double, nullable=False),
)
