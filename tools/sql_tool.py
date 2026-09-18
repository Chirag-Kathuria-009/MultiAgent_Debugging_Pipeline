from langchain_core.tools import  tool
from agents.investigate import get_db_connection
from dotenv import load_dotenv
import re
load_dotenv()




MAX_ROWS = 20

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE)\b",
    re.IGNORECASE,
)



@tool

def run_sql_query(query: str) -> str:
    
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





