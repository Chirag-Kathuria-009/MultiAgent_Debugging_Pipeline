#!/bin/bash
set -e

# Runs once, only when the postgres-db-volume is first created (empty data dir).
# Creates a second, logically separate database + user for the agent's own
# state (LangGraph checkpoints, demo tables) — distinct credentials from the
# "airflow" user/database, but sharing the same Postgres instance.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE "${AGENT_DB_NAME}";
    CREATE USER "${AGENT_DB_USER}" WITH PASSWORD '${AGENT_DB_PASSWORD}';
    GRANT ALL PRIVILEGES ON DATABASE "${AGENT_DB_NAME}" TO "${AGENT_DB_USER}";
    ALTER DATABASE "${AGENT_DB_NAME}" OWNER TO "${AGENT_DB_USER}";
EOSQL