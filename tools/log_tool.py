from langchain_core import tool
from agents.investigate import get_db_connection
from dotenv import load_dotenv
load_dotenv()


MAX_LOG_CHARS = 4000
def _sanitize(log_text: str) -> str:
    
    if len(log_text) > MAX_LOG_CHARS:
        log_text = log_text[:MAX_LOG_CHARS] + "\n...[truncated]"
    return log_text

def make_get_task_logs_tool(failure_context: dict)-> str:
    
    dag_id = failure_context.get("dag_id", "unknown_dag")
    task_id = failure_context.get("task_id", "unknown_task")
    run_id = failure_context.get("run_id", "unknown_run")
    try_number = failure_context.get("try_number", 1)

    @tool
    def get_task_logs() -> str:
        
        raw_log = get_task_instance_logs(dag_id, run_id, task_id, try_number)
        return _sanitize(raw_log)

    return get_task_logs