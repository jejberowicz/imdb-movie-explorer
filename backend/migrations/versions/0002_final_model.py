"""Final model: the remaining columns, the CHECK constraints and the tables that audit each load.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = ("budget", "usa_gross", "worldwide_gross")


def upgrade() -> None:
    for name in ("countries", "languages", "writers", "actors"):
        op.add_column("movies", sa.Column(name, postgresql.ARRAY(sa.Text())))
    op.add_column("movies", sa.Column("production_company", sa.Text()))
    op.add_column("movies", sa.Column("description", sa.Text()))
    op.add_column("movies", sa.Column("metascore", sa.SmallInteger()))
    op.add_column("movies", sa.Column("reviews_from_users", sa.Integer()))
    op.add_column("movies", sa.Column("reviews_from_critics", sa.Integer()))
    for money in MONEY:
        op.add_column("movies", sa.Column(f"{money}_amount", sa.BigInteger()))
        op.add_column("movies", sa.Column(f"{money}_currency", sa.String(3)))

    checks = {
        "movies_id_format": r"imdb_title_id ~ '^tt[0-9]{7,8}$'",
        "movies_year_range": "year BETWEEN 1880 AND 2100",
        "movies_has_genre": "cardinality(genres) >= 1",
        "movies_duration_positive": "duration > 0",
        "movies_avg_vote_range": "avg_vote BETWEEN 1 AND 10",
        "movies_votes_positive": "votes >= 0",
        "movies_metascore_range": "metascore BETWEEN 0 AND 100",
        "movies_user_reviews_positive": "reviews_from_users >= 0",
        "movies_critic_reviews_positive": "reviews_from_critics >= 0",
    }
    for money in MONEY:
        checks[f"movies_{money}_money"] = (
            f"({money}_amount IS NULL) = ({money}_currency IS NULL) AND {money}_amount > 0"
            f" AND {money}_currency ~ '^[A-Z]{{3}}$'"
        )
    for name, condition in checks.items():
        op.create_check_constraint(name, "movies", condition)

    op.create_table(
        "load_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("rows_read", sa.Integer(), nullable=False),
        sa.Column("rows_loaded", sa.Integer(), nullable=False),
        sa.Column("rows_rejected", sa.Integer(), nullable=False),
        sa.Column("corrections", postgresql.JSONB(), nullable=False),
        sa.Column("mean_vote", sa.Double(), nullable=False),
        sa.Column("min_votes", sa.Double(), nullable=False),
    )
    op.create_table(
        "load_rejections",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("load_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("imdb_title_id", sa.Text()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("raw", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("load_rejections")
    op.drop_table("load_runs")
    for name in (
        "movies_id_format",
        "movies_year_range",
        "movies_has_genre",
        "movies_duration_positive",
        "movies_avg_vote_range",
        "movies_votes_positive",
        "movies_metascore_range",
        "movies_user_reviews_positive",
        "movies_critic_reviews_positive",
        *(f"movies_{money}_money" for money in MONEY),
    ):
        op.drop_constraint(name, "movies", type_="check")
    for money in MONEY:
        op.drop_column("movies", f"{money}_currency")
        op.drop_column("movies", f"{money}_amount")
    for name in (
        "reviews_from_critics",
        "reviews_from_users",
        "metascore",
        "description",
        "production_company",
        "actors",
        "writers",
        "languages",
        "countries",
    ):
        op.drop_column("movies", name)
