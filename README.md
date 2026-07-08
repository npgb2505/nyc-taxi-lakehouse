# NYC Taxi Lakehouse Analytics Pipeline

Production-style batch data engineering project for turning official NYC TLC
yellow taxi trip records into governed, tested and analytics-ready lakehouse
marts.

This repository is intentionally written as a portfolio case study. The goal is
not only to show that the code can run, but to make the ETL architecture,
lineage, transformation rules and data quality strategy clear to a hiring
manager or data engineering reviewer.

![NYC Taxi Lakehouse ETL Architecture](docs/architecture-etl.svg)

## Executive Summary

NYC taxi trip files are monthly operational datasets. They are useful for
analytics only after they are landed, cleaned, validated, modeled and published
as business-facing data products.

This project implements a local lakehouse pipeline with:

| Capability | Implementation |
|---|---|
| Batch ingestion | Python downloader for official monthly NYC TLC Parquet files |
| Raw data lake | Partitioned `data/raw/yellow/year=YYYY/month=MM/` landing zone |
| Warehouse engine | DuckDB database for bronze, silver and gold schemas |
| Transformations | SQL and dbt-style models for staging, intermediate and mart layers |
| Data quality | Python quality gates, dbt tests, pytest and markdown quality report |
| Orchestration | Airflow DAG: generate or ingest -> build lakehouse -> validate |
| CI/CD | GitHub Actions runs demo, tests and dbt checks on every push |

Official data source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

## Business Questions

The pipeline creates trusted tables for mobility, marketplace and city
operations use cases:

- Which pickup boroughs and zones generate the most gross revenue?
- How does taxi demand change by hour and day?
- Which days have the strongest airport trip volume?
- Are raw trips clean enough before analysts use them?
- How many records are rejected by quality rules?

## ETL Design

The project uses an ELT-style lakehouse pattern:

1. Extract official monthly Parquet files from NYC TLC.
2. Load them unchanged into a raw landing zone.
3. Transform data inside DuckDB from bronze to silver to gold.
4. Validate curated outputs before publishing marts.

### Extract

`scripts/ingest_tlc.py` downloads official TLC Parquet files:

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
```

Files are saved into a partitioned raw zone:

```text
data/raw/yellow/year=2024/month=01/yellow_tripdata_2024-01.parquet
```

The repository also includes `scripts/generate_sample_data.py` so reviewers can
run the full pipeline without downloading large files.

### Load

Raw files are not overwritten or normalized at ingestion time. DuckDB reads them
as an external bronze view:

```sql
bronze.yellow_trips
```

This keeps raw data replayable and makes schema-on-read behavior explicit.

### Transform

`scripts/build_lakehouse.py` creates three warehouse layers:

| Layer | Object | Grain | Purpose |
|---|---|---|---|
| Bronze | `bronze.yellow_trips` | raw TLC row | Preserve original trip records |
| Bronze | `bronze.taxi_zones` | one row per taxi zone | Reference lookup for borough and zone names |
| Silver | `silver.yellow_trips_clean` | one valid trip | Cleaned and typed trip fact table |
| Gold | `gold.mart_hourly_demand` | date and hour | Demand, passengers, duration, distance, revenue |
| Gold | `gold.mart_zone_revenue` | pickup borough and zone | Zone revenue leaderboard |
| Gold | `gold.mart_airport_trips` | date | Airport trip volume, revenue and tip behavior |

## Data Lineage

```text
NYC TLC Parquet
  -> data/raw/yellow/year=YYYY/month=MM/*.parquet
  -> bronze.yellow_trips
  -> silver.yellow_trips_clean
  -> gold.mart_hourly_demand
  -> gold.mart_zone_revenue
  -> gold.mart_airport_trips
  -> data/marts/*.csv
```

## Transformation Rules

The silver layer applies the rules that make raw trips safe for analysis:

| Rule | Reason |
|---|---|
| `dropoff_at > pickup_at` | Removes impossible trip windows |
| `trip_distance BETWEEN 0.1 AND 100` | Removes zero-distance and extreme outliers |
| `total_amount BETWEEN 0 AND 1000` | Blocks invalid fare values |
| pickup and dropoff location IDs must exist | Protects zone-level joins |
| airport flag derived from `RatecodeID`, JFK and LaGuardia zones | Enables airport-specific analytics |
| duration, pickup date, hour and day name are derived | Supports time-based marts |

## dbt Model Design

The dbt project mirrors the warehouse design and gives reviewers a familiar
analytics engineering structure:

```text
dbt/models/staging/stg_yellow_trips.sql
dbt/models/intermediate/int_trip_enriched.sql
dbt/models/marts/mart_hourly_demand.sql
dbt/models/marts/mart_zone_revenue.sql
dbt/models/marts/mart_airport_trips.sql
```

| dbt Model | Role |
|---|---|
| `stg_yellow_trips` | Stable staging interface over the silver layer |
| `int_trip_enriched` | Adds pickup/dropoff zone names and payment labels |
| `mart_hourly_demand` | Demand and revenue by pickup hour |
| `mart_zone_revenue` | Pickup zone revenue and trip performance |
| `mart_airport_trips` | Airport trip volume, revenue, tips and duration |

## Data Quality Strategy

The pipeline fails before publishing unreliable marts. Quality is checked in
three places:

| Layer | Tool | What It Proves |
|---|---|---|
| Pipeline | `scripts/data_quality.py` | Critical business rules pass |
| Models | dbt tests | Keys and required fields are valid |
| Repository | pytest | The full demo rebuilds expected marts |
| CI | GitHub Actions | The project is reproducible from a clean checkout |

Quality gates:

| Check | Failure Meaning |
|---|---|
| `silver_has_rows` | No usable trip data reached the curated layer |
| `no_negative_amounts` | Fare or revenue values are invalid |
| `valid_trip_duration` | Trip windows are impossible or extreme |
| `valid_distance` | Distance values are not analytically usable |
| `location_keys_present` | Zone joins would be broken |

Generated report:

```text
reports/data_quality_report.md
```

## Orchestration

The Airflow DAG in `airflow/dags/nyc_taxi_lakehouse_dag.py` represents the
production schedule:

```text
generate_sample_data or ingest_tlc
  -> build_lakehouse
  -> run_quality_checks
```

In a cloud version, this DAG can be adapted to:

- download the latest monthly TLC file,
- write raw files to S3 or ADLS,
- build marts in DuckDB, BigQuery, Snowflake or Databricks,
- alert on failed quality gates.

## Failure Modes Handled

| Failure Mode | Handling |
|---|---|
| Empty ingestion | `silver_has_rows` fails |
| Bad fares | negative or extreme amount checks fail |
| Impossible trips | duration and distance checks fail |
| Missing locations | location key check fails |
| Broken model contract | dbt tests fail |
| Non-reproducible repo | GitHub Actions fails |

## Repository Structure

```text
.
|-- .github/workflows/ci.yml
|-- airflow/dags/nyc_taxi_lakehouse_dag.py
|-- dbt/
|   |-- dbt_project.yml
|   |-- profiles.yml
|   `-- models/
|       |-- staging/
|       |-- intermediate/
|       `-- marts/
|-- docs/
|   |-- architecture-etl.svg
|   `-- data_contract.md
|-- scripts/
|   |-- ingest_tlc.py
|   |-- generate_sample_data.py
|   |-- build_lakehouse.py
|   |-- data_quality.py
|   `-- run_demo.py
|-- tests/test_pipeline_contracts.py
|-- docker-compose.yml
`-- requirements.txt
```

## How To Run

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the local reproducible demo:

```powershell
python scripts\run_demo.py --rows 500
```

Run dbt:

```powershell
cd dbt
dbt debug --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

Run tests:

```powershell
pytest
```

Run Airflow:

```powershell
docker compose up
```

## Outputs

| Output | Description |
|---|---|
| `data/warehouse/taxi_lakehouse.duckdb` | Local DuckDB warehouse |
| `data/marts/mart_hourly_demand.csv` | Hourly demand and revenue mart |
| `data/marts/mart_zone_revenue.csv` | Pickup zone performance mart |
| `data/marts/mart_airport_trips.csv` | Airport trip analytics mart |
| `reports/data_quality_report.md` | Quality check evidence |

## What This Demonstrates

- Raw-to-gold lakehouse design.
- Batch ingestion from public Parquet files.
- Partitioned raw landing strategy.
- SQL transformations with business rules.
- dbt modeling and tests.
- Airflow orchestration.
- Quality gates that fail the pipeline.
- CI that proves the project rebuilds from scratch.
- README and architecture documentation written for technical review.

## Interview Talking Points

- I preserved raw files separately from curated tables so the pipeline can be replayed.
- I used bronze, silver and gold layers to separate ingestion, cleaning and business marts.
- I added data quality checks before consumption because a mart is only valuable if it is trustworthy.
- I included dbt tests and CI so the project is not just a local notebook or one-off script.
- I modeled outputs around business questions: hourly demand, zone revenue and airport trips.

## CV Bullet

Built an end-to-end NYC taxi lakehouse pipeline using Python, DuckDB, dbt,
Airflow and GitHub Actions to ingest official Parquet trip records, preserve raw
data, transform trips through bronze/silver/gold layers, enforce data quality
gates and publish tested demand, revenue and airport-trip marts.
