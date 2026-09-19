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

def clear_task_instance(dag_id: str, run_id: str, task_id: str) -> str:
    """
    Clears the state of a specific task instance in Airflow.

    Args:
        dag_id (str): The ID of the DAG.
        run_id (str): The ID of the DAG run.
        task_id (str): The ID of the task.

    Returns:
        bool: True if the task instance was cleared successfully, False otherwise.
    """
    url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{dag_id}/clearTaskInstances"    
    
    payload = {
        "dry_run": False,
        "reset_dag_runs": False,
        "only_failed": True,
        "include_subdags": False,
        "include_parentdag": False,
        "task_ids": [task_id],
        "dag_run_id": run_id
    }
    try:
            
        response = requests.post(url, auth=Auth,json=payload, timeout=10)
        response.raise_for_status()
            
        data = response.json()
        cleared = data.get("task_instances", [])
            
        if cleared:
            return f"cleared {len(cleared)} task instance(s) for {task_id} in run {run_id}"
        return f"WARNING: clear request succeeded but reported 0 task instances cleared for {task_id} in run {run_id}"
    except requests.exceptions.RequestException as e:
        print(f"Failed to clear task instance in Airflow API: {e}. Please check if Airflow is running and accessible.")
        return "Clear task instance failed."
     
