from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = Path("/opt/airflow/project")


with DAG(
    dag_id="nyc_taxi_lakehouse",
    description="Ingest, transform and validate NYC TLC taxi lakehouse marts.",
    start_date=datetime(2024, 1, 1),
    schedule="@monthly",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    dagrun_timeout=timedelta(minutes=30),
    max_active_runs=1,
    tags=["portfolio", "lakehouse", "duckdb", "dbt"],
) as dag:
    generate_sample = BashOperator(
        task_id="generate_sample_data",
        bash_command=f"cd {PROJECT_DIR} && python scripts/generate_sample_data.py --rows 1000 --invalid-rows 5",
        execution_timeout=timedelta(minutes=10),
    )

    build_lakehouse = BashOperator(
        task_id="build_lakehouse",
        bash_command=f"cd {PROJECT_DIR} && python scripts/build_lakehouse.py",
        execution_timeout=timedelta(minutes=15),
    )

    run_quality_checks = BashOperator(
        task_id="run_quality_checks",
        bash_command=f"cd {PROJECT_DIR} && python scripts/data_quality.py",
        execution_timeout=timedelta(minutes=5),
    )

    generate_sample >> build_lakehouse >> run_quality_checks
