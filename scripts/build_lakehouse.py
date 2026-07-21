from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "taxi_lakehouse.duckdb"
MART_DIR = ROOT / "data" / "marts"
RAW_GLOB = (ROOT / "data" / "raw" / "yellow" / "**" / "*.parquet").as_posix()
ZONES_CSV = (ROOT / "data" / "raw" / "reference" / "taxi_zone_lookup.csv").as_posix()


def q(path: str) -> str:
    return path.replace("'", "''")


def build_lakehouse(
    db_path: Path = DB_PATH,
    mart_dir: Path = MART_DIR,
    raw_glob: str = RAW_GLOB,
    zones_csv: str = ZONES_CSV,
) -> dict[str, float]:
    if not list((ROOT / "data" / "raw" / "yellow").glob("**/*.parquet")):
        raise FileNotFoundError("No trip parquet files found. Run generate_sample_data.py or ingest_tlc.py first.")
    if not Path(zones_csv).exists():
        raise FileNotFoundError(f"Taxi zone lookup not found: {zones_csv}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    mart_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")
        con.execute("CREATE SCHEMA IF NOT EXISTS gold")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW bronze.yellow_trips AS
            SELECT *
            FROM read_parquet('{q(raw_glob)}', hive_partitioning = true, union_by_name = true);
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE bronze.taxi_zones AS
            SELECT * FROM read_csv_auto('{q(zones_csv)}', header = true);
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE silver.yellow_trips_rejected AS
            SELECT
                *,
                concat_ws('; ',
                    CASE WHEN tpep_pickup_datetime IS NULL THEN 'missing_pickup_at' END,
                    CASE WHEN tpep_dropoff_datetime IS NULL THEN 'missing_dropoff_at' END,
                    CASE WHEN tpep_dropoff_datetime <= tpep_pickup_datetime THEN 'invalid_time_order' END,
                    CASE
                        WHEN date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) > 360
                        THEN 'duration_over_360_minutes'
                    END,
                    CASE
                        WHEN trip_distance IS NULL OR trip_distance NOT BETWEEN 0.1 AND 100
                        THEN 'invalid_distance'
                    END,
                    CASE WHEN fare_amount IS NULL OR fare_amount < 0 THEN 'invalid_fare' END,
                    CASE WHEN total_amount IS NULL OR total_amount NOT BETWEEN 0 AND 1000 THEN 'invalid_total' END,
                    CASE WHEN PULocationID IS NULL THEN 'missing_pickup_location' END,
                    CASE WHEN DOLocationID IS NULL THEN 'missing_dropoff_location' END
                ) AS rejection_reason
            FROM bronze.yellow_trips
            WHERE tpep_pickup_datetime IS NULL
               OR tpep_dropoff_datetime IS NULL
               OR tpep_dropoff_datetime <= tpep_pickup_datetime
               OR date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) > 360
               OR trip_distance IS NULL OR trip_distance NOT BETWEEN 0.1 AND 100
               OR fare_amount IS NULL OR fare_amount < 0
               OR total_amount IS NULL OR total_amount NOT BETWEEN 0 AND 1000
               OR PULocationID IS NULL OR DOLocationID IS NULL;
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE silver.yellow_trips_clean AS
            SELECT
                row_number() OVER (
                    ORDER BY tpep_pickup_datetime, PULocationID, DOLocationID
                ) AS trip_sk,
                CAST(tpep_pickup_datetime AS TIMESTAMP) AS pickup_at,
                CAST(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_at,
                CAST(date_trunc('day', tpep_pickup_datetime) AS DATE) AS pickup_date,
                EXTRACT(hour FROM tpep_pickup_datetime) AS pickup_hour,
                strftime(tpep_pickup_datetime, '%A') AS pickup_day_name,
                CAST(passenger_count AS INTEGER) AS passenger_count,
                CAST(trip_distance AS DOUBLE) AS trip_distance,
                CAST(PULocationID AS INTEGER) AS pickup_location_id,
                CAST(DOLocationID AS INTEGER) AS dropoff_location_id,
                CAST(payment_type AS INTEGER) AS payment_type,
                CAST(fare_amount AS DOUBLE) AS fare_amount,
                CAST(tip_amount AS DOUBLE) AS tip_amount,
                CAST(tolls_amount AS DOUBLE) AS tolls_amount,
                CAST(total_amount AS DOUBLE) AS total_amount,
                CAST(RatecodeID AS INTEGER) AS rate_code_id,
                date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) AS duration_minutes,
                CASE
                    WHEN RatecodeID = 2
                      OR PULocationID IN (132, 138)
                      OR DOLocationID IN (132, 138)
                    THEN 1 ELSE 0
                END AS is_airport_trip
            FROM bronze.yellow_trips
            WHERE tpep_pickup_datetime IS NOT NULL
              AND tpep_dropoff_datetime IS NOT NULL
              AND tpep_dropoff_datetime > tpep_pickup_datetime
              AND date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) <= 360
              AND trip_distance BETWEEN 0.1 AND 100
              AND fare_amount >= 0
              AND total_amount BETWEEN 0 AND 1000
              AND PULocationID IS NOT NULL
              AND DOLocationID IS NOT NULL;
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE gold.mart_hourly_demand AS
            SELECT
                pickup_date,
                pickup_hour,
                pickup_day_name,
                count(*) AS trips,
                sum(passenger_count) AS passengers,
                round(avg(duration_minutes), 2) AS avg_duration_minutes,
                round(avg(trip_distance), 2) AS avg_trip_distance,
                round(sum(total_amount), 2) AS gross_revenue
            FROM silver.yellow_trips_clean
            GROUP BY 1, 2, 3
            ORDER BY pickup_date, pickup_hour;
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE gold.mart_zone_revenue AS
            SELECT
                coalesce(z.Borough, 'Unknown') AS pickup_borough,
                coalesce(z.Zone, 'Unknown') AS pickup_zone,
                count(*) AS trips,
                round(sum(t.total_amount), 2) AS gross_revenue,
                round(sum(t.tip_amount), 2) AS tips,
                round(avg(t.trip_distance), 2) AS avg_trip_distance,
                round(avg(t.total_amount), 2) AS avg_ticket
            FROM silver.yellow_trips_clean t
            LEFT JOIN bronze.taxi_zones z
                ON t.pickup_location_id = z.LocationID
            GROUP BY 1, 2
            ORDER BY gross_revenue DESC;
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE gold.mart_airport_trips AS
            SELECT
                pickup_date,
                count(*) AS airport_trips,
                round(sum(total_amount), 2) AS airport_revenue,
                round(avg(tip_amount / nullif(total_amount, 0)), 4) AS avg_tip_rate,
                round(avg(duration_minutes), 2) AS avg_duration_minutes
            FROM silver.yellow_trips_clean
            WHERE is_airport_trip = 1
            GROUP BY 1
            ORDER BY pickup_date;
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE gold.pipeline_run_summary AS
            WITH metrics AS (
                SELECT
                    (SELECT count(*) FROM bronze.yellow_trips) AS raw_rows,
                    (SELECT count(*) FROM silver.yellow_trips_clean) AS clean_rows,
                    (SELECT count(*) FROM silver.yellow_trips_rejected) AS rejected_rows,
                    (SELECT count(DISTINCT pickup_location_id) FROM silver.yellow_trips_clean) AS pickup_zones,
                    (SELECT count(*) FROM silver.yellow_trips_clean WHERE is_airport_trip = 1) AS airport_trips,
                    (SELECT round(sum(total_amount), 2) FROM silver.yellow_trips_clean) AS gross_revenue
            )
            SELECT
                *,
                round(100.0 * clean_rows / nullif(raw_rows, 0), 2) AS acceptance_rate_pct,
                current_timestamp AS completed_at
            FROM metrics;
            """
        )

        for table in [
            "mart_hourly_demand",
            "mart_zone_revenue",
            "mart_airport_trips",
            "pipeline_run_summary",
        ]:
            out = (mart_dir / f"{table}.csv").as_posix()
            con.execute(f"COPY gold.{table} TO '{q(out)}' (HEADER, DELIMITER ',')")

        columns = [
            "raw_rows",
            "clean_rows",
            "rejected_rows",
            "pickup_zones",
            "airport_trips",
            "gross_revenue",
            "acceptance_rate_pct",
        ]
        values = con.execute(
            """
            SELECT raw_rows, clean_rows, rejected_rows, pickup_zones,
                   airport_trips, gross_revenue, acceptance_rate_pct
            FROM gold.pipeline_run_summary
            """
        ).fetchone()
        summary = dict(zip(columns, values, strict=True))

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the NYC taxi DuckDB lakehouse and analytics marts.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--mart-dir", type=Path, default=MART_DIR)
    parser.add_argument("--raw-glob", default=RAW_GLOB)
    parser.add_argument("--zones-csv", default=ZONES_CSV)
    args = parser.parse_args()

    summary = build_lakehouse(args.db_path, args.mart_dir, args.raw_glob, args.zones_csv)
    print(f"Built {args.db_path}")
    print(f"Exported marts to {args.mart_dir}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
