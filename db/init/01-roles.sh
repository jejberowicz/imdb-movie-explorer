#!/bin/sh
# Runs once, when PostgreSQL creates the database (docker-entrypoint-initdb.d).
#
# Three roles, each with the least it needs:
# - the superuser (POSTGRES_USER) only administers, and only from inside this container;
# - movies owns the database and the tables: it runs the migrations and the load, but it is not a superuser, so
#   whoever got its password still couldn't run commands on the server (COPY ... TO PROGRAM);
# - movies_api is the user of the API, which can only read. If the API had a bug, or someone found an
#   injection, it still couldn't change or delete data.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v database="$POSTGRES_DB" -v owner_password="$MOVIES_DB_PASSWORD" -v api_password="$API_DB_PASSWORD" <<'SQL'
CREATE ROLE movies LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'owner_password';
-- As the owner of the database, movies can create the tables in public and the pg_trgm extension (trusted).
ALTER DATABASE :"database" OWNER TO movies;

CREATE ROLE movies_api LOGIN PASSWORD :'api_password';
-- No query of the API can hold the database for long; the slowest real one takes a few hundredths of a second.
ALTER ROLE movies_api SET statement_timeout = '5s';
-- A second barrier besides the grants: every transaction of the API is read-only.
ALTER ROLE movies_api SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE :"database" TO movies_api;
GRANT USAGE ON SCHEMA public TO movies_api;
-- The tables don't exist yet: the migrations create them later, as the owner. They are born readable.
ALTER DEFAULT PRIVILEGES FOR ROLE movies IN SCHEMA public GRANT SELECT ON TABLES TO movies_api;
SQL

# The superuser can't log in over the network, with any password: only with psql inside this container
# (docker compose exec db psql -U postgres). pg_hba.conf takes the first line that matches, so this goes first.
sed -i "1i host all $POSTGRES_USER all reject" "$PGDATA/pg_hba.conf"
