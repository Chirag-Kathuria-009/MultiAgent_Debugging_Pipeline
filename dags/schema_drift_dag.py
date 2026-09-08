## cover scenario where schema drift is detected and handled 

##compare schema for both tables orders and orders_drifted in case of drift provide area 
from datetime import datetime

from sqlalchemy import table
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from db_conn import get_db_connection
from airflow.exceptions import AirflowException
from failure_listener import notify_agent
## create two task with input variable 

def read_orders_table(**context):
    conn = get_db_connection()
    conn.autocommit = True
    
    schema_drift_flag = str(Variable.get("schema_drift_flag", default_var=False)).lower() == "true"
    table = "orders_drifted" if schema_drift_flag else "orders"
    
    print(f"Using table: {table}")
    with conn.cursor() as cursor:
        query = f"SELECT customer_id, product_sku, amount FROM {table} ;"
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        
        finally:
            conn.close()
    
    
    context["ti"].xcom_push(key="row_count", value=len(rows))
    print(f"Rows fetched from {table}: {len(rows)}")

def process_orders(**context):
    processed_row_count = context["ti"].xcom_pull(key="row_count", task_ids="read_orders_table")
    print(f"Processed rows: {processed_row_count}")


#### defining structure of DAG for this scenario
with DAG(
    dag_id="schema_drift_dag",
    description="DAG to handle schema drift scenario",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "on_failure_callback": notify_agent,  # Notify the agent on any task failure
    },
    tags = ["failure_demo","schema_drift","self_healing"],
) as dag:
    task1 = PythonOperator(
        task_id="read_orders_table",
        python_callable=read_orders_table,
        retries=0,
    )

    task2 = PythonOperator(
        task_id="process_orders",
        python_callable=process_orders,
        retries=0,
    )
# I want to call task2 only if task1 is successful or there is no schema drift detected. If task1 fails due to schema drift, I want to skip task2 and log the error message.
    task1>>task2


