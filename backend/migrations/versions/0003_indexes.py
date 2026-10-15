"""Indexes for the search, the default order and the genre and country filters.

Each one is justified with EXPLAIN ANALYZE before and after (docs/performance.md).

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pg_trgm is a trusted extension: the owner of the database can create it without being a superuser.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # LIKE '%...%' over the folded titles; patterns shorter than 3 characters can't use them (pg_trgm)
    op.execute(
        "CREATE INDEX movies_original_title_search_trgm ON movies USING gin (original_title_search gin_trgm_ops)"
    )
    op.execute("CREATE INDEX movies_italian_title_search_trgm ON movies USING gin (italian_title_search gin_trgm_ops)")
    # The default order (ADR 0008), with the tiebreaker of the stable pagination
    op.execute("CREATE INDEX movies_weighted_rating ON movies (weighted_rating DESC, imdb_title_id)")
    # Array containment and overlap for the filters: genres @> ARRAY[...], countries && ARRAY[...]
    op.execute("CREATE INDEX movies_genres ON movies USING gin (genres)")
    op.execute("CREATE INDEX movies_countries ON movies USING gin (countries)")


def downgrade() -> None:
    for name in (
        "movies_countries",
        "movies_genres",
        "movies_weighted_rating",
        "movies_italian_title_search_trgm",
        "movies_original_title_search_trgm",
    ):
        op.execute(f"DROP INDEX {name}")
