from __future__ import annotations

from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "taxi_lakehouse.duckdb"
MART_DIR = ROOT / "data" / "marts"
RAW_GLOB = (ROOT / "data" / "raw" / "yellow" / "**" / "*.parquet").as_posix()
ZONES_CSV = (ROOT / "data" / "raw" / "reference" / "taxi_zone_lookup.csv").as_posix()


def q(path: str) -> str:
    return path.replace("'", "''")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    MART_DIR.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(DB_PATH)) as con:
        con.execute("INSTALL parquet; LOAD parquet;")
        con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")
        con.execute("CREATE SCHEMA IF NOT EXISTS gold")

        con.execute(
            f"""
            CREATE OR REPLACE VIEW bronze.yellow_trips AS
            SELECT * FROM read_parquet('{q(RAW_GLOB)}', hive_partitioning = true, union_by_name = true);
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE bronze.taxi_zones AS
            SELECT * FROM read_csv_auto('{q(ZONES_CSV)}', header = true);
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE silver.yellow_trips_clean AS
            SELECT
                row_number() OVER () AS trip_sk,
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
                CASE WHEN RatecodeID = 2 OR PULocationID IN (132, 138) OR DOLocationID IN (132, 138) THEN 1 ELSE 0 END AS is_airport_trip
            FROM bronze.yellow_trips
            WHERE tpep_pickup_datetime IS NOT NULL
              AND tpep_dropoff_datetime IS NOT NULL
              AND tpep_dropoff_datetime > tpep_pickup_datetime
              AND trip_distance BETWEEN 0.1 AND 100
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
            CREATE OR REPLACE TABLE gold.data_quality_summary AS
            SELECT 'raw_rows' AS metric, count(*)::DOUBLE AS value FROM bronze.yellow_trips
            UNION ALL
            SELECT 'clean_rows', count(*)::DOUBLE FROM silver.yellow_trips_clean
            UNION ALL
            SELECT 'rejected_rows', (
                (SELECT count(*) FROM bronze.yellow_trips) - (SELECT count(*) FROM silver.yellow_trips_clean)
            )::DOUBLE
            UNION ALL
            SELECT 'gross_revenue', round(sum(total_amount), 2) FROM silver.yellow_trips_clean;
            """
        )

        for table in ["mart_hourly_demand", "mart_zone_revenue", "mart_airport_trips", "data_quality_summary"]:
            out = (MART_DIR / f"{table}.csv").as_posix()
            con.execute(f"COPY gold.{table} TO '{q(out)}' (HEADER, DELIMITER ',')")

    print(f"Built {DB_PATH}")
    print(f"Exported marts to {MART_DIR}")


if __name__ == "__main__":
    main()
