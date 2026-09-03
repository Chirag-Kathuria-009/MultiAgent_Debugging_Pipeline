"""
flaky_etl_dag
---------------
Failure category: UPSTREAM TIMEOUT / transient error.

Simulates a call to a flaky upstream service. This is the ONE scenario
deliberately designed to be fixed by a simple retry — matching the case
your Remediate agent's allow-list should auto-execute later without human
approval.

Behavior when armed (Variable "upstream_timeout_active" = "true"):
  - Fails on the FIRST attempt (try_number == 1) with a timeout-style error.
  - Succeeds on any subsequent attempt (try_number >= 2).
Behavior when disarmed ("false", default): always succeeds immediately.

retries=0 is deliberate: Airflow must NOT auto-retry this task on its own,
or the failure would resolve itself before your agent ever saw it happen.
The "retry" that fixes this task instance is meant to come later from your
Remediate agent clearing/re-running it via the Airflow REST API — that's
the entire point of this scenario. To see the recovery yourself right now,
CLEAR the failed task instance (don't re-trigger the whole DAG — a new run
resets try_number back to 1).

Arm it:   airflow variables set upstream_timeout_active true
Disarm:   airflow variables set upstream_timeout_active false

Note: dag_id is kept as "upstream_timeout_pipeline" (not "flaky_etl...")
to stay consistent with the Triage-category naming used elsewhere in this
project — only the filename matches what you asked for.
"""
from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from db_conn import get_db_connection  # confirm this matches the function name in your db_conn.py


def call_flaky_upstream(**context):
    armed = str(Variable.get("upstream_timeout_active", default_var="false")).lower() == "true"
    try_number = context["ti"].try_number

    if armed and try_number == 1:
        raise AirflowException(
            "Upstream service timeout: connection to partner-api.example.internal "
            "timed out after 30s (attempt 1)"
        )

    # "Succeeded" — touch the DB so there's a real trace this run completed,
    # giving the Investigate agent something concrete to point to later.
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders;")
            count = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"Upstream call succeeded on attempt {try_number}. Orders table has {count} rows.")


def process_result(**context):
    print("Processing result from upstream call")


with DAG(
    dag_id="upstream_timeout_pipeline",
    description="Demo pipeline simulating a transient upstream timeout, fixable by retry",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["failure-demo", "upstream-timeout", "self-healing-agent"],
) as dag:

    call = PythonOperator(
        task_id="call_flaky_upstream",
        python_callable=call_flaky_upstream,
        retries=0,  # do not let Airflow itself retry — see module docstring
    )

    process = PythonOperator(
        task_id="process_result",
        python_callable=process_result,
    )

    call >> process