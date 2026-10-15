"""Create the movies table with what the list and the search need.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "movies",
        sa.Column("imdb_title_id", sa.Text(), primary_key=True),
        sa.Column("original_title", sa.Text(), nullable=False),
        sa.Column("italian_title", sa.Text(), nullable=False),
        sa.Column("original_title_search", sa.Text(), nullable=False),
        sa.Column("italian_title_search", sa.Text(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("genres", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("directors", postgresql.ARRAY(sa.Text())),
        sa.Column("duration", sa.SmallInteger(), nullable=False),
        sa.Column("avg_vote", sa.Numeric(3, 1), nullable=False),
        sa.Column("votes", sa.Integer(), nullable=False),
        sa.Column("weighted_rating", sa.Double(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("movies")
