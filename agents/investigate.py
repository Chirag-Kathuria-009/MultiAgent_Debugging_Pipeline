from state import AgentState
import os
import psycopg2
from tools.sql_tool import run_sql_query, list_columns
from tools.log_tool import make_get_task_logs_tool
from dotenv import load_dotenv
load_dotenv()



from langchain_core import tool
   
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


def investigate_node(state: AgentState) -> dict:
    log = state.get("agent_log", [])
    failure_context = state.get("failure_context", {})
    print(f"Received failure context: {failure_context}")
    dag_id = failure_context.get("dag_id", "unknown_dag")
    task_id = failure_context.get("task_id", "unknown_task")
    
    # fetching results from triage 
    triage_category = state.get("triage_category")
    triage_justification = state.get("triage_justification")
    

