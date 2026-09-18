#!/bin/bash
set -e

# Runs once, only when postgres-db-volume is first created (empty data dir).
# Creates a dedicated READ-ONLY role for the Investigate agent's SQL tool —
# separate from "agent" (owns pipeline_agent, can write/drop anything) and
# separate from "airflow" (cluster superuser, bypasses all privilege checks).
# This is the actual enforcement of "the tool is read-only" — a database
# privilege, not just app-level query filtering.
#
# Note: this runs before the seed DAG ever creates orders/orders_drifted/
# orders_quality_check, so at THIS moment there are no tables yet — the
# ALTER DEFAULT PRIVILEGES line is what actually matters here, since it
# applies automatically once those tables get created later.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$AGENT_DB_NAME" <<-EOSQL
    CREATE ROLE ${INVESTIGATOR_DB_USER} WITH LOGIN PASSWORD '${INVESTIGATOR_DB_PASSWORD}';
    GRANT CONNECT ON DATABASE ${AGENT_DB_NAME} TO ${INVESTIGATOR_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${INVESTIGATOR_DB_USER};
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${INVESTIGATOR_DB_USER};

    ALTER DEFAULT PRIVILEGES FOR ROLE ${AGENT_DB_USER} IN SCHEMA public
        GRANT SELECT ON TABLES TO ${INVESTIGATOR_DB_USER};
EOSQL