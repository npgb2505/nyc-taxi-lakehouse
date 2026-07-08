from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow.operators.bash import BashOperator
from airflow import DAG


PROJECT_DIR = Path("/opt/airflow/project")


with DAG(
    dag_id="nyc_taxi_lakehouse",
    description="Ingest, transform and validate NYC TLC taxi lakehouse marts.",
    start_date=datetime(2024, 1, 1),
    schedule="@monthly",
    catchup=False,
    tags=["portfolio", "lakehouse", "duckdb", "dbt"],
) as dag:
    generate_sample = BashOperator(
        task_id="generate_sample_data",
        bash_command=f"cd {PROJECT_DIR} && python scripts/generate_sample_data.py --rows 1000",
    )

    build_lakehouse = BashOperator(
        task_id="build_lakehouse",
        bash_command=f"cd {PROJECT_DIR} && python scripts/build_lakehouse.py",
    )

    run_quality_checks = BashOperator(
        task_id="run_quality_checks",
        bash_command=f"cd {PROJECT_DIR} && python scripts/data_quality.py",
    )

    generate_sample >> build_lakehouse >> run_quality_checks
