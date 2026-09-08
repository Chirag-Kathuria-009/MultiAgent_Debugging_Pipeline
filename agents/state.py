"""
Shared state schema for the self-healing pipeline agent's LangGraph graph.
 
This is the single object that flows through every node (triage ->
investigate -> remediate -> report). Each node reads what it needs and
returns a partial update — LangGraph merges it into the running state,
nodes never need to reconstruct the whole object.
"""

from typing import Optional, TypedDict, List

class FailureContext(TypedDict,total=False):
    """
    Contextual information about the failure that triggered the self-healing
    pipeline agent.
    """
    dag_id: str
    failure_time: str
    run_id: str
    try_number: int
    error_message: str
    log_url: Optional[str]
    execution_date: Optional[str]
    affected_tables: Optional[List[str]]
    

class AgentState(TypedDict,total=False):
    """
    The shared state schema for the self-healing pipeline agent's LangGraph graph.
    """
    failure_context: FailureContext
    triage_category: Optional[str] # "schema_drift" | "null_spike" | "upstream_timeout" | "unknown" (Updated by triage_node)
    triage_justification: Optional[str] #(Updated by triage_node)
    investigation_findings: Optional[str] #(Updated by investigate_node)
    investigation_evidence: Optional[str] #(Updated by investigate_node)
    proposed_action: Optional[str] #(Updated by remediate_node)
    risk_level: Optional[str] # "low" | "medium" | "high" (Updated by remediate_node)
    automated_action_taken: Optional[bool] # Updated by remediate_node
    
    approval_status: Optional[str] # "approved" | "rejected" | "pending"
    incident_summary: Optional[str] # Updated by report_node
    agent_log: list
    
    