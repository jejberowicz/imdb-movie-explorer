"""Database tables, described with SQLAlchemy Core. The Alembic migrations create them."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

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
    # The A-Z key: the folded original title without the symbols at its start; NULL if it has nothing else
    Column(
        "title_sort",
        Text,
        Computed(r"nullif(regexp_replace(original_title_search, '^[^[:alnum:]]+', ''), '')", persisted=True),
    ),
    Column("year", SmallInteger, nullable=False),
    Column("genres", ARRAY(Text), nullable=False),
    Column("directors", ARRAY(Text)),
    Column("duration", SmallInteger, nullable=False),
    Column("avg_vote", Numeric(3, 1), nullable=False),
    Column("votes", Integer, nullable=False),
    Column("weighted_rating", Double, nullable=False),
    Column("countries", ARRAY(Text)),
    # "None" means a movie without dialogue (ADR 0003, rule 7)
    Column("languages", ARRAY(Text)),
    Column("writers", ARRAY(Text)),
    Column("actors", ARRAY(Text)),
    Column("production_company", Text),
    Column("description", Text),
    Column("metascore", SmallInteger),
    Column("reviews_from_users", Integer),
    Column("reviews_from_critics", Integer),
    # Amounts in their own currency, never converted (ADR 0003, rule 3)
    Column("budget_amount", BigInteger),
    Column("budget_currency", String(3)),
    Column("usa_gross_amount", BigInteger),
    Column("usa_gross_currency", String(3)),
    Column("worldwide_gross_amount", BigInteger),
    Column("worldwide_gross_currency", String(3)),
    CheckConstraint(r"imdb_title_id ~ '^tt[0-9]{7,8}$'", name="movies_id_format"),
    CheckConstraint("year BETWEEN 1880 AND 2100", name="movies_year_range"),
    CheckConstraint("cardinality(genres) >= 1", name="movies_has_genre"),
    CheckConstraint("duration > 0", name="movies_duration_positive"),
    CheckConstraint("avg_vote BETWEEN 1 AND 10", name="movies_avg_vote_range"),
    CheckConstraint("votes >= 0", name="movies_votes_positive"),
    CheckConstraint("metascore BETWEEN 0 AND 100", name="movies_metascore_range"),
    CheckConstraint("reviews_from_users >= 0", name="movies_user_reviews_positive"),
    CheckConstraint("reviews_from_critics >= 0", name="movies_critic_reviews_positive"),
    *(
        CheckConstraint(
            f"({money}_amount IS NULL) = ({money}_currency IS NULL) AND {money}_amount > 0"
            f" AND {money}_currency ~ '^[A-Z]{{3}}$'",
            name=f"movies_{money}_money",
        )
        for money in ("budget", "usa_gross", "worldwide_gross")
    ),
)

# One row per load: what file it was, what happened and the constants of the weighted rating.
load_runs = Table(
    "load_runs",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("loaded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("source", Text, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("rows_read", Integer, nullable=False),
    Column("rows_loaded", Integer, nullable=False),
    Column("rows_rejected", Integer, nullable=False),
    Column("corrections", JSONB, nullable=False),
    Column("mean_vote", Double, nullable=False),
    Column("min_votes", Double, nullable=False),
)

# Rejected rows are kept with their original content and the reason, not lost (ADR 0003).
load_rejections = Table(
    "load_rejections",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("run_id", BigInteger, ForeignKey("load_runs.id", ondelete="CASCADE"), nullable=False),
    Column("line_number", Integer, nullable=False),
    Column("imdb_title_id", Text),
    Column("reason", Text, nullable=False),
    Column("raw", JSONB, nullable=False),
)
