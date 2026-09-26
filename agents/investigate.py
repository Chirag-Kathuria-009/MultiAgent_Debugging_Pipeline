from langchain_google_genai import ChatGoogleGenerativeAI

from agents.state import AgentState
import os
import psycopg2
from tools.sql_tool import run_sql_query, list_columns
from tools.log_tool import make_get_task_logs_tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from dotenv import load_dotenv
load_dotenv()


INVESTIGATE_MODEL = os.environ.get("INVESTIGATE_MODEL", "gemini-3.8-flash")
 
MAX_ITERATIONS = 5
 
INVESTIGATE_SYSTEM_PROMPT = """You are the investigation agent for a self-healing data pipeline.
 
You are given a failure that already went through a preliminary triage
step, which assigned it a likely category. Treat that classification as a
HYPOTHESIS, not a fact — your job is to gather real evidence with your
tools and either confirm it or correct it. Do not simply restate the
triage classification without verifying it against actual data or logs.
 
You have three tools:
- get_task_logs: fetches the full log for the failed task (no arguments needed)
- list_columns: lists a table's columns and data types, given a table name
- run_sql_query: runs a read-only SELECT query you write yourself
 
Use as few tool calls as you need to reach a confident, evidence-backed
conclusion. When you are ready, respond with a final answer in plain
text: a concise explanation of the root cause, citing the specific
evidence (log text, column names, query results) that supports it. Do
not call any more tools once you're giving your final answer.
"""

   

def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            parts.append(block.get("text", "") if isinstance(block, dict) else str(block))
        return "".join(parts)
    return str(content)

def investigate_agent(state: AgentState) -> dict:
    log = list(state.get("agent_log", []))
    failure_context = state.get("failure_context", {})
    print(f"Received failure context: {failure_context}")
    dag_id = failure_context.get("dag_id", "unknown_dag")
    task_id = failure_context.get("task_id", "unknown_task")
    
    # fetching results from triage 
    triage_category = state.get("triage_category")
    triage_justification = state.get("triage_justification")
    
    tools = [make_get_task_logs_tool(failure_context), list_columns, run_sql_query]
    
    tools_by_name = {t.name: t for t in tools}
    
    llm = ChatGoogleGenerativeAI(model=INVESTIGATE_MODEL, temperature=0.0)
    llm_with_tools = llm.bind_tools(tools)
    
    human_prompt = (
        f"failure_context: {failure_context}\n"
        f"triage_category (hypothesis, not fact): {triage_category}\n"
        f"triage_justification: {triage_justification}\n"
    )
    
    messages = [
        SystemMessage(content=INVESTIGATE_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt)
    ]
    
    evidence = []
    findings = "Investigation did not complete."  # overwritten in every real path below
    
    try:
        for _ in range(MAX_ITERATIONS):
            response: AIMessage = llm_with_tools.invoke(messages)
            # response IS already a complete AIMessage — append it directly,
            # do not wrap it or pass it as a keyword argument.
            messages.append(response)
            
            if not response.tool_calls:
                findings = _extract_text(response.content)
                break
            print(f"Tool calls: {response.tool_calls}")
            
            for tool_call in response.tool_calls:
                tool_to_call = tools_by_name.get(tool_call["name"])
                if tool_to_call is None:
                    result = f"ERROR: unknown tool '{tool_call['name']}'"
                else:
                    result = tool_to_call.invoke(tool_call["args"])
                
                evidence.append({"tool": tool_call["name"], "input": tool_call["args"], "output": result})
                log.append(f"[investigate] called {tool_call['name']}({tool_call['args']})")
 
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
        else:
            findings = (
                f"Investigation stopped after {MAX_ITERATIONS} tool calls without a "
                f"conclusive answer. Evidence gathered: {evidence}"
            )
        
            
    except Exception as e:
        findings = f"Investigate LLM call failed: {e}"

    log.append(f"[investigate] findings: {findings}")
    print(log[-1])
    
    return {
        "investigation_findings": findings,
        "investigation_evidence": {"tool_calls": evidence},
        "agent_log": log,
    }
        
    
    
    

