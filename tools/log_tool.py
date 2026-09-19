from langchain_core.tools import tool
from dotenv import load_dotenv
from tools.airflow_api import get_task_instance_logs
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
        """Fetch the full task log for the failed task currently being
        investigated. Use this when the short exception message alone
        isn't enough to reach a conclusion — the full log may contain
        earlier warnings, retry history, or surrounding context that
        explains what actually happened. Takes no arguments — it already
        knows which task instance to fetch, since there is only one
        relevant to this investigation."""
        raw_log = get_task_instance_logs(dag_id, run_id, task_id, try_number)
        return _sanitize(raw_log)

    return get_task_logs