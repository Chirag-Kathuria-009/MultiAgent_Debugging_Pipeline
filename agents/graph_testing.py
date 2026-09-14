"""
Quick standalone check for Phase 2's core plumbing — no FastAPI, no Docker
networking involved at all. Run this FIRST, before testing anything
through Airflow, to isolate whether the graph + checkpointer themselves
work, independent of HTTP or container networking.
 
Run from the project root:
    python test_graph_standalone.py
"""
import os
 
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
 
from agents.graph import build_graph
 
load_dotenv()
 
AGENT_DB_USER = os.environ.get("AGENT_DB_USER", "agent")
AGENT_DB_PASSWORD = os.environ.get("AGENT_DB_PASSWORD", "agent")
AGENT_DB_NAME = os.environ.get("AGENT_DB_NAME", "pipeline_agent")
AGENT_DB_HOST_PORT = os.environ.get("AGENT_DB_HOST_PORT", "5442")
 
DB_URI = (
    f"postgresql://{AGENT_DB_USER}:{AGENT_DB_PASSWORD}"
    f"@localhost:{AGENT_DB_HOST_PORT}/{AGENT_DB_NAME}?sslmode=disable"
)
 
fake_failure = {
    "failure_context": {
        "dag_id": "test_dag",
        "task_id": "test_task",
        "run_id": "manual_test_run",
        "try_number": 1,
        "exception_message": "this is a fake failure for standalone testing",
        "log_url": None,
        "execution_date": None,
    },
    "agent_log": [],
}
 
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    graph = build_graph(checkpointer)
    print("EDGES:", graph.get_graph().edges)
    print("NODES:", graph.get_graph().nodes)
    print("Graph compiled successfully.")
    result = graph.invoke(fake_failure, config={"configurable": {"thread_id": "standalone-test-1"}})
 
print("\n--- Final state ---")
for key, value in result.items():
    print(f"{key}: {value}")

'''
http://localhost:8090/trigger-diagnosis -H "Content-Type: application/json" -d "{\"dag_id\":\"test\",\"task_id\":\"t1\",\"run_id\":\"r1\",\"try_number\":1,\"exception_message\":\"fake\"}\"` should trigger the same four print statements in the uvicorn console. This proves the FastAPI layer works, still with zero Airflow or Docker networking involved.'''
