from state import AgentState

def investigate_node(state: AgentState) -> dict:
    log = state.get("agent_log", [])
    failure_context = state.get("failure_context", {})
    print(f"Received failure context: {failure_context}")
    dag_id = failure_context.get("dag_id", "unknown_dag")
    task_id = failure_context.get("task_id", "unknown_task")
    
    # fetching results from triage 
    triage_category = state.get("triage_category")
    triage_justification = state.get("triage_justification")
    
    