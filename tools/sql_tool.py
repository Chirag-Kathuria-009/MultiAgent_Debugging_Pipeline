from langchain_core.tools import  tool
from dotenv import load_dotenv
import re
load_dotenv()
import psycopg2
import os



MAX_ROWS = 20

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE)\b",
    re.IGNORECASE,
)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("AGENT_DB_HOST", "postgres"),
        port=os.environ.get("AGENT_DB_HOST_PORT", "5442"),
        dbname=os.environ.get("AGENT_DB_NAME", "pipeline_agent"),
        user=os.environ.get("INVESTIGATOR_DB_USER", "investigator_ro"),
        password=os.environ.get("INVESTIGATOR_DB_PASSWORD", "investigator_ro")
    )
    
    conn.readonly = True  # Set the connection to read-only mode
    return conn

@tool
def run_sql_query(query: str) -> str:
    
    """Execute a read-only SQL SELECT query against the pipeline
    database and return the matching rows. Use this to check real data —
    row counts, null rates, sample values, or anything else needed to
    confirm or rule out a hypothesis about the failure. Only SELECT
    statements are permitted; anything else is rejected before it
    reaches the database. Results are capped at 20 rows — use your own
    LIMIT or an aggregate (COUNT, etc.) if you need a summary rather
    than raw rows."""
    
    if FORBIDDEN_KEYWORDS.search(query):
        return "Error: Forbidden SQL operation detected. Only SELECT queries are allowed."
    
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            if cursor.description is None:
                    return "Query executed but returned no rows (was this a SELECT?)."
            columns = [desc.name for desc in cursor.description]
            results = cursor.fetchmany(MAX_ROWS)
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return f"Error executing SQL query: {e}" 
    
    
    if not results:
        return "No results found."
    
    lines = [" | ".join(columns)]
    for row in results:
        lines.append(" | ".join(str(v) for v in row))
    return "\n".join(lines)


@tool
def list_columns(table_name: str) -> str:
    """List the column names and data types of a table in the pipeline
    database. Use this before writing a query against a table you're not
    already certain about the shape of — faster and safer than guessing
    column names, and directly useful for spotting schema drift (a
    column that's missing, renamed, or has an unexpected type)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
            columns = cursor.fetchall()
    except Exception as e:
        return f"Error listing columns for table {table_name}: {e}"
    
    if not columns:
        return f"No columns found for table {table_name}."
    
    return "\n".join(f"{name}: {dtype}" for name, dtype in columns)





