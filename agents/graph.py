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
import time 

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
    log.append("[investigate] placeholder — no real investigation yet")
    print(log[-1])
    return {"investigation_findings": "placeholder", "agent_log": log}

def remediate_node(state: AgentState) -> dict:
    log = list(state.get("agent_log", []))
    log.append("[remediate] placeholder — no real remediation yet")
    print(log[-1])
    return {"proposed_action": "placeholder", "risk_level": "low", "automated_action_taken": False, "agent_log": log}

def report_node(state: AgentState) -> dict:
    log = list(state.get("agent_log", []))
    log.append("[report] placeholder — no real report yet")
    print(log[-1])
    return {"incident_summary": "placeholder", "agent_log": log}


def route_after_remediate(state: AgentState) -> str:
    """
    Decide whether to route to report_node or back to triage_node after remediation.
    
    if state.get("automated_action_taken"):
        return "report_node"
    else:
        return "triage_node"""
    
    return "report_node"  # Placeholder logic for now

def build_graph(checkpointer) -> StateGraph:
    """
    Build the LangGraph graph for the self-healing pipeline agent.
    """
    graph = StateGraph(AgentState)

    graph.add_node("triage_node", triage_node)
    graph.add_node("investigate_node", investigate_node)
    graph.add_node("remediate_node", remediate_node)
    graph.add_node("report_node", report_node)

    graph.add_edge(START, "triage_node")
    graph.add_edge("triage_node", "investigate_node")
    graph.add_edge("investigate_node", "remediate_node")
    graph.add_conditional_edges(
        "remediate_node",
        route_after_remediate,
        {"report_node": "report_node"},
    )
    graph.add_edge("report_node", END)

    return graph.compile(checkpointer=checkpointer)



    