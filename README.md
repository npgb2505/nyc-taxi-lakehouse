# NYC Taxi Lakehouse Analytics Pipeline

An end-to-end data engineering portfolio project that turns NYC TLC yellow taxi
trip records into tested, analytics-ready lakehouse marts.

The project is designed to demonstrate the work a data engineer does in a real
analytics platform: ingesting external files, preserving raw data, cleaning and
modeling trips, enforcing quality rules, scheduling a pipeline, and publishing
business-friendly marts.

## Why This Project Matters

Taxi trips are operational events: they arrive monthly, contain messy edge
cases, and become useful only after they are modeled into reliable metrics. This
pipeline answers questions a city operations, mobility, or marketplace analytics
team would actually care about:

- Which pickup zones generate the most revenue?
- How does demand change by hour and day?
- How much revenue comes from airport trips?
- Are trip records passing basic quality gates before analysts use them?

## Architecture

```text
NYC TLC Parquet files
        |
        v
data/raw/yellow/year=YYYY/month=MM/
        |
        v
DuckDB bronze schema
        |
        v
silver.yellow_trips_clean
        |
        v
dbt-style gold marts
        |
        v
CSV marts + quality report
```

## Tech Stack

| Layer | Tools |
|---|---|
| Ingestion | Python, Requests, NYC TLC Parquet |
| Storage | Local data lake folder, DuckDB |
| Transformation | SQL, dbt project structure |
| Quality | Python checks, dbt tests |
| Orchestration | Apache Airflow DAG |
| Packaging | Docker Compose |
| Testing | pytest |

## Repository Structure

```text
.
|-- airflow/dags/                 # Airflow orchestration
|-- dbt/models/                   # Staging, intermediate, marts
|-- docs/data_contract.md         # Contract and quality expectations
|-- scripts/
|   |-- generate_sample_data.py   # Small deterministic sample for demos/tests
|   |-- ingest_tlc.py             # Real NYC TLC monthly file ingestion
|   |-- build_lakehouse.py        # Bronze, silver, gold DuckDB pipeline
|   |-- data_quality.py           # Quality gates and markdown report
|   `-- run_demo.py               # One-command local demo
|-- tests/                        # Pipeline contract tests
|-- docker-compose.yml
`-- README.md
```

## Quick Start

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the full local demo:

```powershell
python scripts\run_demo.py --rows 500
```

Run tests:

```powershell
pytest
```

The demo creates:

- `data/warehouse/taxi_lakehouse.duckdb`
- `data/marts/mart_hourly_demand.csv`
- `data/marts/mart_zone_revenue.csv`
- `data/marts/mart_airport_trips.csv`
- `reports/data_quality_report.md`

## Ingest Real NYC TLC Data

The demo uses synthetic sample data so the GitHub repository stays lightweight.
To ingest an official NYC TLC monthly Parquet file:

```powershell
python scripts\ingest_tlc.py --trip-type yellow --year 2024 --month 1
python scripts\build_lakehouse.py
python scripts\data_quality.py
```

Official source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

## Airflow Demo

Start Airflow:

```powershell
docker compose up
```

Open `http://localhost:8080`, then trigger the `nyc_taxi_lakehouse` DAG. The DAG
runs the same pipeline steps used by the local demo:

1. Generate or ingest raw data.
2. Build bronze, silver and gold layers.
3. Run quality gates.

## Data Quality Gates

The pipeline fails if the curated silver layer violates critical rules:

| Check | Purpose |
|---|---|
| `silver_has_rows` | Prevents empty downstream marts |
| `no_negative_amounts` | Blocks invalid fare/revenue records |
| `valid_trip_duration` | Removes impossible trip windows |
| `valid_distance` | Removes zero or extreme distance records |
| `location_keys_present` | Protects zone-level joins |

## Gold Marts

| Mart | Business Use |
|---|---|
| `gold.mart_hourly_demand` | Staffing, demand forecasting, peak-hour analysis |
| `gold.mart_zone_revenue` | Zone performance and revenue concentration |
| `gold.mart_airport_trips` | Airport trip behavior, revenue, tipping and duration |

## Portfolio Talking Points

- Built a local lakehouse pipeline with raw, silver and gold layers.
- Implemented deterministic sample data so reviewers can run the project quickly.
- Added data quality gates that fail the pipeline before bad data reaches marts.
- Modeled analytics tables for demand, revenue and airport trip analysis.
- Included Airflow orchestration and dbt models to mirror a modern analytics engineering workflow.

## CV Bullet

Built an end-to-end NYC taxi lakehouse pipeline using Python, DuckDB, dbt and
Airflow to ingest Parquet trip records, validate data quality, transform raw
events into curated marts, and publish revenue, demand and airport-trip analytics.
