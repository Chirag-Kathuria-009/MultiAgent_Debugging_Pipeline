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
 
THREAD_ID = "standalone-test-1"  # MUST exactly match what test_graph_standalone.py used
 
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = build_graph(checkpointer)
    result = graph.invoke(None, config={"configurable": {"thread_id": THREAD_ID}})
 
print("\n--- Resumed final state ---")
for key, value in result.items():
    print(f"{key}: {value}")