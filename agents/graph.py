"""
LangGraph skeleton for the self-healing pipeline agent.
 
Phase 2 goal: prove the plumbing works end to end with placeholder nodes
that do nothing but log and pass state along. Phase 3-7 replace each
placeholder with the real agent logic — the graph's shape doesn't change,
only what happens inside each node.
 
build_graph() takes a checkpointer rather than creating one internally, so
the caller (service.py) owns the checkpointer's connection lifecycle.
"""

from langgraph.graph import END, START, StateGraph
from agents.state import AgentState
from agents.triage_agent import triage_agent
from agents.investigate import investigate_agent
from agents.remediate import remediate_agent
from langgraph.types import interrupt, Command
import time
from tools.airflow_api import clear_task_instance
from agents.report import report_agent

def triage_node(state: AgentState) -> dict:
    """
    Placeholder triage node for the self-healing pipeline agent.
    """
    log = list(state.get("agent_log", []))
    
    result = triage_agent(state)
    log.extend(result["agent_log"])

    #log.append(f"[triage] placeholder — received failure: {state.get('failure_context')}")
    print("Recent log entry:", log[-1])
    #return {"triage_category": "unknown", "triage_justification": "placeholder-not-yet-implemented", "agent_log": log}
    return result

def investigate_node(state: AgentState) -> dict:
    print("Working with Investigate node...")
    #tStimulating delay for demonstration purposes
    #time.sleep(15)
    log = list(state.get("agent_log", []))
    result = investigate_agent(state)
    log.extend(result["agent_log"])
    #log.append("[investigate] placeholder — no real investigation yet")
    print(log[-1])
    return result

def remediate_node(state: AgentState) -> dict:
    log = list(state.get("agent_log", []))
    result = remediate_agent(state)
    log.extend(result["agent_log"])
    #log.append("[remediate] placeholder — no real remediation yet")
    print(log[-1])
    return result

def report_node(state: AgentState) -> dict:
    log = list(state.get("agent_log", []))
    result = report_agent(state)
    log.extend(result["agent_log"])
    print(log[-1])
    return result


def route_after_remediate(state: AgentState) -> str:
    """
    Decide whether to route to report_node or back to triage_node after remediation.
    
    if state.get("automated_action_taken"):
        return "report_node"
    else:
        return "triage_node"""
    
    return "auto_executed" if state.get("auto_executed") else "needs_approval"  # Placeholder logic for now

# addition of new node for handling human approval
def approval_node(state: AgentState) -> dict:
    log = list(state.get("agent_log",[]))
    failure_context = state.get("failure_context",{})
    proposed_action = state.get("proposed_action","")
    action_type = proposed_action.split(":", 1)[0].strip() if proposed_action else "unknown"
    
    decision = interrupt({
        "question": "Do you approve the proposed remediation?",
        "context": failure_context,
        "triage_category": state.get("triage_category"),
        "investigation_findings": state.get("investigation_findings"),
        "proposed_action": proposed_action,
        "action_type": action_type,
        "risk_level": state.get("risk_level"),
    })
    
    decision = (decision or {}).get("decision", "reject")
    log.append(f"[approval] human decision received: {decision}")
 
    if decision == "approve" and action_type == "retry":
        result = clear_task_instance(
            dag_id=failure_context.get("dag_id"),
            run_id=failure_context.get("run_id"),
            task_id=failure_context.get("task_id"),
        )
        log.append(f"[approval] approved action executed: {result}")
        approval_status = "approved"
    elif decision == "approve":
        # Approved, but "escalate" (or anything else) isn't something
        # this system can execute automatically. Approval here means
        # "a human has reviewed and acknowledged this," not "and it ran."
        log.append(f"[approval] approved (acknowledged) — no automatic action exists for '{action_type}'")
        approval_status = "approved"
    else:
        log.append("[approval] rejected — no action taken")
        approval_status = "rejected"
 
    print(log[-1])
 
    return {
        "approval_status": approval_status,
        "agent_log": log,
    }

def build_graph(checkpointer) -> StateGraph:
    """
    Build the LangGraph graph for the self-healing pipeline agent.
    """
    graph = StateGraph(AgentState)

    graph.add_node("triage_node", triage_node)
    graph.add_node("investigate_node", investigate_node)
    graph.add_node("remediate_node", remediate_node)
    graph.add_node("report_node", report_node)
    graph.add_node("approval_node", approval_node)
    graph.add_edge(START, "triage_node")
    graph.add_edge("triage_node", "investigate_node")
    graph.add_edge("investigate_node", "remediate_node")
    graph.add_edge("approval_node", "report_node")
    graph.add_conditional_edges(
        "remediate_node",
        route_after_remediate,
        {
            "auto_executed": "report_node",
            "needs_approval": "approval_node"
        }
    )
    graph.add_edge("report_node", END)
    
    

    return graph.compile(checkpointer=checkpointer)



    