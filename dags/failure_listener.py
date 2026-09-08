import os
import requests

AGENT_SERVICE_URL = os.environ.get(
    "AGENT_SERVICE_URL", "http://host.docker.internal:8090/trigger-diagnosis"
)


def notify_agent(context):
    ti = context["ti"]
    exception = context.get("exception")
    
    payload = {
        "dag_id": context["dag"].dag_id,
        "task_id": context["task"].task_id,
        "execution_date": str(context["execution_date"]),
        "try_number": ti.try_number,
        "exception": str(exception) if exception else "Not Available",
        "run_id": context["run_id"],
        "log_url": ti.log_url,
    }
    
    try:
        response = requests.post(AGENT_SERVICE_URL, json=payload,timeout=5)
        #response.raise_for_status()
        print(f"Successfully notified the agent: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to notify the agent: {e}.Couldnt reach agent service at {AGENT_SERVICE_URL}. Please check if the agent service is running and accessible.")
