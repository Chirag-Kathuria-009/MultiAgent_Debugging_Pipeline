import os
import psycopg2

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("AGENT_DB_HOST","postgres"),
        port=os.environ.get("AGENT_DB_PORT","5432"),
        dbname=os.environ.get("AGENT_DB_NAME","pipeline_agent"),
        user=os.environ.get("AGENT_DB_USER","agent"),
        password=os.environ.get("AGENT_DB_PASSWORD","agent")
    )
# self_healing_agent-postgres-1