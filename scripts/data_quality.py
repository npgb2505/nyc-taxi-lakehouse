from __future__ import annotations

from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "taxi_lakehouse.duckdb"
REPORT_PATH = ROOT / "reports" / "data_quality_report.md"


CHECKS = {
    "silver_has_rows": "SELECT CASE WHEN count(*) > 0 THEN 0 ELSE 1 END FROM silver.yellow_trips_clean",
    "no_negative_amounts": "SELECT count(*) FROM silver.yellow_trips_clean WHERE total_amount < 0 OR fare_amount < 0",
    "valid_trip_duration": "SELECT count(*) FROM silver.yellow_trips_clean WHERE duration_minutes <= 0 OR duration_minutes > 360",
    "valid_distance": "SELECT count(*) FROM silver.yellow_trips_clean WHERE trip_distance <= 0 OR trip_distance > 100",
    "location_keys_present": "SELECT count(*) FROM silver.yellow_trips_clean WHERE pickup_location_id IS NULL OR dropoff_location_id IS NULL",
}


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[str, int]] = []

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        rows = []
        for name, sql in CHECKS.items():
            failed_rows = int(con.execute(sql).fetchone()[0])
            status = "PASS" if failed_rows == 0 else "FAIL"
            rows.append((name, status, failed_rows))
            if failed_rows:
                failures.append((name, failed_rows))

        mart_counts = con.execute(
            """
            SELECT 'gold.mart_hourly_demand' AS table_name, count(*) AS rows FROM gold.mart_hourly_demand
            UNION ALL
            SELECT 'gold.mart_zone_revenue', count(*) FROM gold.mart_zone_revenue
            UNION ALL
            SELECT 'gold.mart_airport_trips', count(*) FROM gold.mart_airport_trips
            """
        ).fetchall()

    lines = [
        "# Data Quality Report",
        "",
        "| Check | Status | Failed Rows |",
        "|---|---:|---:|",
    ]
    lines += [f"| {name} | {status} | {failed_rows} |" for name, status, failed_rows in rows]
    lines += ["", "## Mart Row Counts", "", "| Table | Rows |", "|---|---:|"]
    lines += [f"| {table} | {count} |" for table, count in mart_counts]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")

    if failures:
        for name, failed_rows in failures:
            print(f"FAIL {name}: {failed_rows}")
        raise SystemExit(1)
    print("All data quality checks passed")


if __name__ == "__main__":
    main()
