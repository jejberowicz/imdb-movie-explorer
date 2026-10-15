"""The API reads only the two tables it queries: movies, and load_runs for the readiness check and the catalog cache.

Each table that the API has to read gets its GRANT here, by name, instead of every new table being born readable:
load_rejections keeps the raw rows that the load set aside, and the API has no use for them.

movies_api is created by db/init/01-roles.sh, only in Docker. Where it doesn't exist (the tests, a local database),
there is nothing to grant.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'movies_api') THEN
                -- A database created before this migration gave the API every table of the owner, present and
                -- future: take that back.
                EXECUTE format(
                    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE SELECT ON TABLES FROM movies_api',
                    current_user
                );
                REVOKE ALL ON load_rejections, alembic_version FROM movies_api;
                GRANT SELECT ON movies, load_runs TO movies_api;
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'movies_api') THEN
                REVOKE SELECT ON movies, load_runs FROM movies_api;
            END IF;
        END
        $$
    """)
