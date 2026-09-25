import os
from contextlib import asynccontextmanager
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel
from langgraph.types import Command
from agents.graph import build_graph
from agents.state import FailureContext

load_dotenv()  # Load environment variables from .env file

AGENT_DB_HOST_PORT = os.environ.get("AGENT_DB_HOST_PORT", "5432")
AGENT_DB_NAME = os.environ.get("AGENT_DB_NAME", "pipeline_agent")
AGENT_DB_USER = os.environ.get("AGENT_DB_USER", "agent")
AGENT_DB_PASSWORD = os.environ.get("AGENT_DB_PASSWORD", "agent")


DB_URI = (
    f"postgresql://{AGENT_DB_USER}:{AGENT_DB_PASSWORD}"
    f"@localhost:{AGENT_DB_HOST_PORT}/{AGENT_DB_NAME}?sslmode=disable"
)

# Populated 

graph_state = {"graph": None, "checkpointer": None }

pending_approvals : dict[str,dict] = {}  # Maps thread_id to state dict for pending approvals


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the PostgresSaver for checkpointing
    checkpointer = PostgresSaver.from_conn_string(DB_URI) # here we are reading checkpoint information from postgres
    checkpointer_start = checkpointer.__enter__()
    checkpointer_start.setup()
    
    
    graph_state["checkpointer"] = checkpointer

    # Build the graph and store it in the global state
    graph = build_graph(checkpointer_start)
    graph_state["graph"] = graph
    
    print(f"Agent service ready. Checkpointer connected to {AGENT_DB_NAME}@localhost:{AGENT_DB_HOST_PORT}")
    yield
    checkpointer.__exit__(None, None, None)
    # This is where the application runs

app = FastAPI(title="Agent Service", lifespan=lifespan)

class FailurePayload(BaseModel):
    dag_id: str
    task_id: str
    execution_date: str
    try_number: int
    exception: str
    run_id: str
    log_url: str
    
class ApprovalRequest(BaseModel):
    thread_id: str

def _resume_thread(thread_id: str, decision: Literal["approval","rejected"])-> dict:
    if thread_id not in pending_approvals:
        return {"status": "error", "message": f"No pending approval found for thread_id={thread_id}"}
    
    result = graph_state["graph"].invoke(
        Command(resume={"decision":decision}),
        config = {"configurable": {"thread_id": thread_id}}
    )
    
    pending_approvals.pop(thread_id, None)  # Remove the pending approval after resuming
    print(f"[service] thread_id={thread_id} resumed with decision={decision}")
    return {"status": f"{decision}d", "thread_id": thread_id, "final_state": result}

@app.post("/trigger-diagnosis")
def trigger_diagnosis(payload: FailurePayload):
    thread_id = f"{payload.dag_id}:{payload.task_id}:{payload.run_id}"
 
    initial_state = {
        "failure_context": payload.model_dump(),
        "agent_log": [],
    }
 
    result = graph_state["graph"].invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
    print(f"[DEBUG] raw graph result keys: {list(result.keys())}")
    
    if "__interrupt__" in result:
        interrupt_payload = result["__interrupt__"][0].value
        pending_approvals[thread_id] = interrupt_payload
        print(f"Diagnosis PAUSED for thread_id={thread_id} — awaiting human approval")
        return {"status": "pending_approval", "thread_id": thread_id, "approval_payload": interrupt_payload}
        
    print(f"Diagnosis graph completed for thread_id={thread_id}")
    return {"status": "completed", "thread_id": thread_id, "final_state": result}
 


@app.post("/approve")
def approve(request: ApprovalRequest):
    return _resume_thread(request.thread_id, "approve")
 
 
@app.post("/reject")
def reject(request: ApprovalRequest):
    return _resume_thread(request.thread_id, "reject")
 
 
@app.get("/pending-approvals")
def list_pending_approvals():
    return {"pending": pending_approvals}

 
APPROVAL_UI_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Self-Healing Pipeline — Approvals</title>
<style>
  body { font-family: -apple-system, Segoe UI, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; max-width: 900px; margin: 0 auto; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .sub { color:#94a3b8; margin-bottom: 24px; font-size: 13px; }
  .empty { color:#64748b; padding: 40px; text-align:center; border: 1px dashed #334155; border-radius: 8px; }
  .card { background:#1e293b; border:1px solid #334155; border-radius:10px; padding:16px 20px; margin-bottom:16px; }
  .card h3 { margin: 0 0 4px 0; font-size:16px; }
  .meta { color:#94a3b8; font-size:12px; margin-bottom:12px; word-break: break-all; }
  .field { margin: 10px 0; }
  .field .label { font-size:11px; text-transform:uppercase; letter-spacing:0.04em; color:#64748b; margin-bottom:3px; }
  .field .value { font-size:14px; line-height:1.5; white-space:pre-wrap; }
  .risk-high { color:#f87171; font-weight:600; }
  .risk-low { color:#4ade80; font-weight:600; }
  .actions { display:flex; gap:10px; margin-top:16px; }
  button { border:none; border-radius:6px; padding:8px 18px; font-size:14px; cursor:pointer; font-weight:600; }
  .approve { background:#16a34a; color:white; }
  .reject { background:#dc2626; color:white; }
  button:disabled { opacity:0.5; cursor:not-allowed; }
  .status { font-size:12px; color:#64748b; margin-top:24px; }
</style>
</head>
<body>
  <h1>Pending Approvals</h1>
  <div class="sub">Self-healing pipeline agent — refreshes every 5s</div>
  <div id="list"><div class="empty">Loading…</div></div>
  <div class="status" id="status"></div>
 
<script>
function escapeHtml(s) {
  const d = document.createElement('div');
  d.innerText = String(s);
  return d.innerHTML.replace(/"/g, '&quot;');
}
 
async function fetchPending() {
  const res = await fetch('/pending-approvals');
  const data = await res.json();
  render(data.pending || {});
}
 
function render(pending) {
  const list = document.getElementById('list');
  const ids = Object.keys(pending);
  if (ids.length === 0) {
    list.innerHTML = '<div class="empty">No pending approvals right now.</div>';
    return;
  }
  list.innerHTML = ids.map(id => cardHtml(id, pending[id])).join('');
}
 
function cardHtml(threadId, payload) {
  const fc = payload.failure_context || {};
  const risk = (payload.risk_level || '').toLowerCase();
  const riskClass = risk === 'high' ? 'risk-high' : 'risk-low';
  return `
    <div class="card" data-thread-id="${escapeHtml(threadId)}">
      <h3>${escapeHtml(fc.dag_id || '')} / ${escapeHtml(fc.task_id || '')}</h3>
      <div class="meta">${escapeHtml(threadId)}</div>
      <div class="field"><div class="label">Triage category</div><div class="value">${escapeHtml(payload.triage_category || '')}</div></div>
      <div class="field"><div class="label">Investigation findings</div><div class="value">${escapeHtml(payload.investigation_findings || '')}</div></div>
      <div class="field"><div class="label">Proposed action</div><div class="value">${escapeHtml(payload.proposed_action || '')}</div></div>
      <div class="field"><div class="label">Risk level</div><div class="value ${riskClass}">${escapeHtml(payload.risk_level || '')}</div></div>
      <div class="actions">
        <button class="approve" data-decision="approve">Approve</button>
        <button class="reject" data-decision="reject">Reject</button>
      </div>
    </div>
  `;
}
 
document.getElementById('list').addEventListener('click', async (e) => {
  const decision = e.target.dataset.decision;
  if (!decision) return;
  const card = e.target.closest('.card');
  const threadId = card.dataset.threadId;
  card.querySelectorAll('button').forEach(b => b.disabled = true);
  const status = document.getElementById('status');
  status.textContent = `Sending ${decision} for ${threadId}...`;
  try {
    const res = await fetch('/' + decision, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({thread_id: threadId})
    });
    const data = await res.json();
    status.textContent = `${decision} result: ${data.status}`;
  } catch (err) {
    status.textContent = 'Error: ' + err;
  }
  fetchPending();
});
 
fetchPending();
setInterval(fetchPending, 5000);
</script>
</body>
</html>
"""
 
 
 
@app.get("/", response_class=HTMLResponse)
def approval_ui():
    return APPROVAL_UI_HTML
 
 
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}
    