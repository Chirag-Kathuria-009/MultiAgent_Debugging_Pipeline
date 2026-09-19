import os
from typing import Literal

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agents.state import AgentState
from guardrails.allowlist import is_allowed
from guardrails.risk_classifier import assess_risk
from tools.airflow_api import clear_task_instance, get_task_instance_logs

load_dotenv()  # Load environment variables from .env file

REMEDIATE_MODEL = os.environ.get("REMEDIATE_MODEL", "gemini-3.5-flash-lite")
 
REMEDIATE_SYSTEM_PROMPT = """You are the remediation agent for a self-healing data pipeline.
 
Given the triage classification and investigation findings for a failure,
propose EXACTLY ONE remediation action, chosen only from:
 
- retry: re-run the failed task. Appropriate ONLY for a transient or
  upstream-timeout failure likely to succeed on a second attempt.
- escalate: do not attempt any automatic fix. Appropriate for anything
  involving a schema change, a data-quality issue, or anything where an
  automatic fix could be wrong or unsafe.
 
Your proposal is a RECOMMENDATION only — a separate, deterministic system
decides whether it is actually allowed to run automatically. Do not assume
your proposal will be executed as-is.
 
action_description must be one sentence explaining why this action fits
the specific evidence from the investigation.
"""

class RemediationProposal(BaseModel):
    action_type: Literal["retry", "escalate"]
    action_description: str = Field(description="One sentence explaining why this action fits the investigation findings")

def get_remediation_llm():
    llm = ChatGoogleGenerativeAI(model=REMEDIATE_MODEL, temperature=0.0)
    print(f"Using remediation model: {REMEDIATE_MODEL} and temperature: {llm.temperature}")
    return llm.with_structured_output(RemediationProposal)

def remediate_agent(state: AgentState)->dict:
    log = list(state.get("agent_log", []))
    failure_context = state.get("failure_context", {})
    
    triage_category = state.get("triage_category","unknown")
    investigation_findings = state.get("investigation_findings","")
    try_number = failure_context.get("try_number", 1)
    
    human_prompt = (
        f"triage_category: {triage_category}\n"
        f"investigation_findings: {investigation_findings}\n"
    )
    
    try:
        structured_llm = get_remediation_llm()
        proposal: RemediationProposal = structured_llm.invoke([
            {"role": "system", "content": REMEDIATE_SYSTEM_PROMPT},
            {"role": "user", "content": human_prompt}
        ])
        
        action_type = proposal.action_type
        action_description = proposal.action_description
        
    except Exception as e:
        action_type = "escalate"
        action_description = f"Error during remediation LLM invocation: {e}. Defaulting to escalate."
    
    log.append(f"[remediate] proposed action: {action_type} with description: {action_description}")
    print(action_type)
    print(action_description)
    risk = assess_risk(action_type)
    allowed = is_allowed(triage_category, action_type,try_number)
    auto_executed = False
    
    #print(f"[remediate] risk level: {risk}, allowed: {allowed}, try_number: {try_number}")
    if allowed and risk == "low" and action_type == "retry":
        result = clear_task_instance(
            dag_id = failure_context.get("dag_id"),
            run_id = failure_context.get("run_id"),
            task_id = failure_context.get("task_id"),
        )
        auto_executed = True
        log.append(f"[remediate] automatically executed action: {action_type}")
    else:
         log.append(
            f"[remediate] NOT auto-executed (allowed={allowed}, risk={risk}) — needs human approval"
        )
 
    print(log[-1])
    
    return {
        "proposed_action": f"{action_type}: {action_description}",
        "risk_level": risk,
        "auto_executed": auto_executed,
        "approval_status": "not_required" if auto_executed else "pending",
        "agent_log": log,
    }