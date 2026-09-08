"""
null_spike_dag
----------------
Failure category: NULL SPIKE / data-quality failure.

Loads a fresh, uniquely-tagged batch of rows into "orders_quality_check"
(customer_id is sometimes NULL, simulating a broken upstream extract), then
checks whether the null rate in THAT batch alone exceeds a threshold.

Toggle via the Airflow Variable "null_spike_pct" (percent of rows that
should be NULL — e.g. "2" for baseline, "40" to trigger a failure).
Threshold is configurable via "threshold_pct" (default 10, meaning 10%).

Each run's batch is tagged with context["run_id"] — a unique identifier
Airflow already generates per DAG run, so there's no extra query and no
race condition, unlike a MAX(batch_id)+1 approach.
"""
import random
from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from failure_listener import notify_agent
from db_conn import get_db_connection  # confirm this matches the function name in your db_conn.py

BATCH_SIZE = 50
SKUS = ["SKU-1001", "SKU-1002", "SKU-1003", "SKU-1004", "SKU-1005"]


def generate_rows(null_row_count, total_row_count):
    null_indices = set(random.sample(range(total_row_count), null_row_count))
    rows = []
    for i in range(total_row_count):
        customer_id = None if i in null_indices else random.randint(100, 200)
        rows.append(
            (
                customer_id,
                random.choice(SKUS),
                round(random.uniform(10.0, 1000.0), 2),
            )
        )
    return rows


def load_batch(**context):
    null_spike_pct = float(Variable.get("null_spike_pct", default_var="2"))
    null_row_count = min(BATCH_SIZE, int((null_spike_pct / 100) * BATCH_SIZE))
    batch_id = context["run_id"]  # unique per run — no query, no race condition

    rows = generate_rows(null_row_count, BATCH_SIZE)

    conn = get_db_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO orders_quality_check (batch_id, customer_id, product_sku, amount) "
                "VALUES (%s, %s, %s, %s);",
                [(batch_id, *row) for row in rows],
            )
    finally:
        conn.close()
    print(f"Loaded batch {batch_id} ({BATCH_SIZE} rows, {null_row_count} intentionally NULL)")
    context["ti"].xcom_push(key="batch_id", value=batch_id)
    context["ti"].xcom_push(key="nulls", value=null_row_count)
    context["ti"].xcom_push(key="total", value=BATCH_SIZE)


def check_null_spike(**context):
    batch_id = context["ti"].xcom_pull(task_ids="load_batch", key="batch_id")
    query = f"SELECT COUNT(*) AS null_count FROM orders_quality_check WHERE batch_id = '{batch_id}' AND customer_id IS NULL;"
    
    conn = get_db_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            null_count = cur.fetchone()[0]
    finally:
        conn.close()

    #nulls = context["ti"].xcom_pull(task_ids="load_batch", key="nulls")
    total = context["ti"].xcom_pull(task_ids="load_batch", key="total")
    threshold_pct = float(Variable.get("threshold_pct", default_var="10"))

    null_pct = (null_count / total * 100) if total else 0
    print(f"Batch {batch_id}: {null_count}/{total} rows have NULL customer_id ({null_pct:.1f}%)")

    if null_pct > threshold_pct:
        raise AirflowException(
            f"Null spike detected in batch {batch_id}: {null_count}/{total} rows "
            f"({null_pct:.1f}%) have NULL customer_id, exceeds threshold of {threshold_pct:.1f}%."
        )
    print(f"No null spike detected in batch {batch_id}.")


with DAG(
    dag_id="null_spike_dag",
    description="Demo pipeline that fails a data-quality null-rate check when armed",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["failure-demo", "null-spike", "self-healing-agent"],
    default_args={
        "on_failure_callback": notify_agent,  # Notify the agent on any task failure
    },
) as dag:

    load = PythonOperator(
        task_id="load_batch",
        python_callable=load_batch,
        retries=0,
    )

    check = PythonOperator(
        task_id="check_null_spike",
        python_callable=check_null_spike,
        retries=0,
    )

    load >> check