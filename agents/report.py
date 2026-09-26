"""
Report agent for the self-healing pipeline agent.

Not an LLM call. By the time this node runs, everything worth knowing is
already sitting in state — triage classified it, investigate gathered
evidence, remediate proposed (and maybe ran) a fix, and approval recorded
a human decision if one was needed. report_agent's only job is to turn
that state into one readable incident record: a summary string for the
API response, and a text file on disk for the audit trail.
"""
import os
import re

from datetime import datetime, timezone

from dotenv import load_dotenv
from agents.state import AgentState
load_dotenv()

REPORTS_DIR = os.environ.get("INCIDENT_REPORTS_DIR", "incident_reports")

def _safe_filename(value: str)->str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value or "unknown")

def _build_summary(state: AgentState)-> str:
    failure_context = state.get("failure_context", {})
    dag_id = failure_context.get("dag_id", "unknown_dag")
    task_id = failure_context.get("task_id", "unknown_task")
    run_id = failure_context.get("run_id", "unknown_run")
    try_number = failure_context.get("try_number", "unknown")
    exception = failure_context.get("exception", "unknown")

    triage_category = state.get("triage_category", "unknown")
    triage_justification = state.get("triage_justification", "")
    investigation_findings = state.get("investigation_findings", "")
    proposed_action = state.get("proposed_action", "")
    risk_level = state.get("risk_level", "unknown")
    auto_executed = state.get("auto_executed", False)
    approval_status = state.get("approval_status", "not_required")
    
    if auto_executed:
        outcome = "Auto-remediated — no human involved."
    elif approval_status == "approved":
        outcome = "Remediated after human approval."
    elif approval_status == "rejected":
        outcome = "Rejected by human reviewer — no action taken."
    else:
        outcome = "Pending human approval."
    
    lines = [
        f"Incident report: {dag_id}.{task_id}",
        f"Run: {run_id} (attempt {try_number})",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Failure: {exception}",
        "",
        f"Triage: {triage_category} — {triage_justification}",
        "",
        f"Investigation findings: {investigation_findings}",
        "",
        f"Proposed action: {proposed_action}",
        f"Risk level: {risk_level}",
        "",
        f"Outcome: {outcome}",
    ]
    return "\n".join(lines)

def report_agent(state: AgentState) -> dict:
    log = list(state.get("agent_log", []))
    failure_context = state.get("failure_context", {}) or {}

    summary = _build_summary(state)

    dag_id = _safe_filename(failure_context.get("dag_id", "unknown_dag"))
    task_id = _safe_filename(failure_context.get("task_id", "unknown_task"))
    run_id = _safe_filename(failure_context.get("run_id", "unknown_run"))

    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"{dag_id}__{task_id}__{run_id}.txt")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(summary)
        log.append(f"[report] incident report written to {path}")
    except OSError as e:
        log.append(f"[report] failed to write incident report: {e}")

    return {
        "incident_summary": summary,
        "agent_log": log,
    }  
    