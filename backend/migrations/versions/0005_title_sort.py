"""The A-Z order skips the symbols at the start of the titles.

"#Alive", "(500) Days of Summer" and "¡Three Amigos!" went before every letter. A title made only of symbols ("$",
"?") has no key and goes to the end.

A generated column, so the database fills it for the movies already loaded and for every new load, with no change
to the load and no second implementation to keep in sync.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE movies ADD COLUMN title_sort text
        GENERATED ALWAYS AS (nullif(regexp_replace(original_title_search, '^[^[:alnum:]]+', ''), '')) STORED
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE movies DROP COLUMN title_sort")
