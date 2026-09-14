import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel

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

@app.post("/trigger-diagnosis")
def trigger_diagnosis(payload: FailurePayload):
    thread_id = f"{payload.dag_id}:{payload.task_id}:{payload.run_id}"
 
    initial_state = {
        "failure_context": payload.model_dump(),
        "agent_log": [],
    }
 
    result = graph_state["graph"].invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
    print(f"Diagnosis graph completed for thread_id={thread_id}")
    return {"status": "completed", "thread_id": thread_id, "final_state": result}
 
 
@app.get("/health")
def health():
    return {"status": "ok"}
    