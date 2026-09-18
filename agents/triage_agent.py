
import os
from typing import Literal

from dotenv import load_dotenv

from agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv  # Load environment variables from .env file

load_dotenv()  # Load environment variables from .env file

triage_model = os.environ.get("TRIAGE_MODEL", "gemini-2.0-flash")

TRIAGE_SYSTEM_PROMPT = """You are a triage classifier for a self-healing data pipeline agent.
 
Classify the failure into EXACTLY ONE of these categories:
- schema_drift: a database error about a missing, renamed, or mismatched column/table/schema
- null_spike: a data-quality check failing due to a null rate or threshold being exceeded
- upstream_timeout: a connection timeout or transient network/service error
- resource_limit: the task ran out of memory, disk, or hit a resource quota
- transform_logic: a bug in the pipeline's own transformation code, unrelated to schema, data quality, or infra
- unknown: none of the above clearly apply, or there isn't enough evidence
 
Classify PRIMARILY from the exception_message text — that is the real evidence.
Treat dag_id and task_id as weak, optional supporting context only. NEVER let
the dag_id or task_id name alone decide the category — a real pipeline's name
tells you nothing reliable about how it might fail.
 
Your justification must be exactly one sentence and must cite the specific
evidence in exception_message that led to your classification.
"""

 
class TriageResult(BaseModel): # importance of creating this model to makesure particular fields contains specific values and other types are rejected straight away. This is important because the triage node is the first node in the graph and it needs to ensure that the state is valid before passing it along to the next nodes.
    triage_category: Literal["schema_drift", "null_spike", "upstream_timeout", "resource_limit", "transform_logic", "unknown"]
    triage_justification: str = Field(description="A one-sentence justification for the triage category, citing specific evidence from the exception_message.")

def _get_triage_llm():
    llm = ChatGoogleGenerativeAI(model = triage_model, temperature=0.0)
    
    print(f"Using triage model: {triage_model} and temperature: {llm.temperature}")
    
    return llm.with_structured_output(TriageResult)
    

def triage_agent(state: AgentState) -> dict:
    """
    Classifies the failure in the AgentState into one of the predefined categories.

    Args:
        state (AgentState): The current state of the agent, containing exception_message, dag_id, and task_id.
    """
    
    log = state.get("agent_log", [])
    failure_context = state.get("failure_context", {})
    print(f"Received failure context: {failure_context}")
    dag_id = failure_context.get("dag_id", "unknown_dag")
    task_id = failure_context.get("task_id", "unknown_task")
    exception_message = failure_context.get("exception", "No exception message provided.")
    
    human_prompt = (
        f"exception_message: {exception_message}\n"
        f"dag_id (weak context only): {dag_id}\n"
        f"task_id (weak context only): {task_id}\n"
    )
    
    try:
        llm = _get_triage_llm()
        result = llm.invoke([
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": human_prompt}
        ])
        print(f"Triage LLM result: {result}")
        category = result.triage_category
        justification = result.triage_justification
    except Exception as e:
        print(f"Error during triage LLM invocation: {e}")
        category = "unknown"
        justification = f"LLM invocation failed with error: {e}"
    
    log.append(f"[triage] classified failure as '{category}' with justification: {justification}")
    print(log[-1])
    
    return {
        "triage_category": category,
        "triage_justification": justification,
        "agent_log": log,
    }

        