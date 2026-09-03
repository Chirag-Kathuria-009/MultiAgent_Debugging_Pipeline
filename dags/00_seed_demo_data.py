"""
00_seed_demo_data
------------------
One-time setup DAG for the self-healing pipeline agent project. Creates the
demo tables used by the three failure-injection DAGs and seeds canonical data.

Trigger this ONCE manually (Airflow UI, or `airflow dags trigger
00_seed_demo_data` from inside the scheduler container) before running
schema_drift_pipeline, null_spike_pipeline, or upstream_timeout_pipeline for
the first time. Safe to re-run any time — it drops and recreates its tables
each run, so re-triggering it resets all demo data to a clean baseline.
"""
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from db_conn import get_db_connection

CANONICAL_ROWS = [
    # (customer_id, product_sku, amount, region)
    (101, "SKU-1001", 49.99, "EU-West"),
    (102, "SKU-1002", 129.50, "EU-Central"),
    (103, "SKU-1003", 15.00, "EU-West"),
    (104, "SKU-1004", 899.00, "EU-North"),
    (105, "SKU-1005", 22.75, "EU-South"),
]


def seed_data():
    conn = get_db_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        # --- canonical "orders" table: the healthy baseline all three
        # failure DAGs read from when their toggle is off ---
        cur.execute("DROP TABLE IF EXISTS orders;")
        cur.execute(
            """
            CREATE TABLE orders (
                order_id SERIAL PRIMARY KEY,
                customer_id INTEGER,
                product_sku VARCHAR(20),
                amount NUMERIC(10,2),
                region VARCHAR(50),
                created_at TIMESTAMP DEFAULT now()
            );
            """
        )
        cur.executemany(
            "INSERT INTO orders (customer_id, product_sku, amount, region) "
            "VALUES (%s, %s, %s, %s);",
            CANONICAL_ROWS,
        )

        # --- "orders_drifted": identical data, but customer_id was renamed
        # to cust_id — simulates an upstream schema change nobody announced ---
        cur.execute("DROP TABLE IF EXISTS orders_drifted;")
        cur.execute(
            """
            CREATE TABLE orders_drifted (
                order_id SERIAL PRIMARY KEY,
                cust_id INTEGER,
                product_sku VARCHAR(20),
                amount NUMERIC(10,2),
                region VARCHAR(50),
                created_at TIMESTAMP DEFAULT now()
            );
            """
        )
        cur.executemany(
            "INSERT INTO orders_drifted (cust_id, product_sku, amount, region) "
            "VALUES (%s, %s, %s, %s);",
            CANONICAL_ROWS,
        )

        # --- "orders_quality_check": landing table the null-spike DAG
        # writes a fresh, tagged batch into on every run ---
        cur.execute("DROP TABLE IF EXISTS orders_quality_check;")
        cur.execute(
            """
            CREATE TABLE orders_quality_check (
                id SERIAL PRIMARY KEY,
                batch_id VARCHAR(50),
                customer_id INTEGER,
                product_sku VARCHAR(20),
                amount NUMERIC(10,2),
                created_at TIMESTAMP DEFAULT now()
            );
            """
        )
    conn.close()
    print("Demo tables created: orders, orders_drifted, orders_quality_check")


with DAG(
    dag_id="00_seed_demo_data",
    description="One-time setup: creates and seeds demo tables for the failure DAGs",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["setup", "self-healing-agent"],
) as dag:

    seed = PythonOperator(
        task_id="seed_demo_data",
        python_callable=seed_data,
    )