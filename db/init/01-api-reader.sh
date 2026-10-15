#!/bin/sh
# Runs once, when PostgreSQL creates the database (docker-entrypoint-initdb.d).
#
# Two roles: the owner (POSTGRES_USER) runs the migrations and the load; the API connects as movies_api, which
# can only read. If the API had a bug, or someone found an injection, it still couldn't change or delete data.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v owner="$POSTGRES_USER" -v database="$POSTGRES_DB" -v api_password="$API_DB_PASSWORD" <<'SQL'
CREATE ROLE movies_api LOGIN PASSWORD :'api_password';
-- No query of the API can hold the database for long; the slowest real one takes a few hundredths of a second.
ALTER ROLE movies_api SET statement_timeout = '5s';
-- A second barrier besides the grants: every transaction of the API is read-only.
ALTER ROLE movies_api SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE :"database" TO movies_api;
GRANT USAGE ON SCHEMA public TO movies_api;
-- The tables don't exist yet: the migrations create them later, as the owner. They are born readable.
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT SELECT ON TABLES TO movies_api;
SQL
