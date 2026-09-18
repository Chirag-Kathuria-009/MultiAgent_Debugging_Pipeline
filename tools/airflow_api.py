import os

import requests
from dotenv import load_dotenv
load_dotenv()

AIRFLOW_BASE_URL = os.environ.get("AIRFLOW_BASE_URL", "http://localhost:8081")
AIRFLOW_API_USER = os.environ.get("AIRFLOW_API_USER", "airflow")
AIRFLOW_API_PASSWORD = os.environ.get("AIRFLOW_API_PASSWORD", "airflow")

Auth = (AIRFLOW_API_USER, AIRFLOW_API_PASSWORD)

def get_task_instance_logs(dag_id: str, run_id: str, task_id: str, try_number: int=1) -> str:
    """
    Fetches the logs for a specific task instance from the Airflow API.

    Args:
        dag_id (str): The ID of the DAG.
        run_id (str): The ID of the DAG run.
        task_id (str): The ID of the task.
        try_number (int): The try number of the task instance.

    Returns:
        str: The logs of the specified task instance.
    """
    url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}"
    
    try:
        response = requests.get(url, auth=Auth, headers={"Accept": "text/plain"}, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch logs from Airflow API: {e}. Please check if Airflow is running and accessible.")
        return "Log retrieval failed."