from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "taxi_lakehouse.duckdb"
REPORT_PATH = ROOT / "reports" / "data_quality_report.md"
JSON_REPORT_PATH = ROOT / "reports" / "data_quality_report.json"


CHECKS = {
    "silver_has_rows": "SELECT CASE WHEN count(*) > 0 THEN 0 ELSE 1 END FROM silver.yellow_trips_clean",
    "no_negative_amounts": "SELECT count(*) FROM silver.yellow_trips_clean WHERE total_amount < 0 OR fare_amount < 0",
    "valid_trip_duration": (
        "SELECT count(*) FROM silver.yellow_trips_clean "
        "WHERE duration_minutes <= 0 OR duration_minutes > 360"
    ),
    "valid_distance": "SELECT count(*) FROM silver.yellow_trips_clean WHERE trip_distance <= 0 OR trip_distance > 100",
    "location_keys_present": (
        "SELECT count(*) FROM silver.yellow_trips_clean "
        "WHERE pickup_location_id IS NULL OR dropoff_location_id IS NULL"
    ),
    "trip_key_unique": "SELECT count(*) - count(DISTINCT trip_sk) FROM silver.yellow_trips_clean",
    "raw_rows_reconciled": (
        "SELECT abs((SELECT count(*) FROM bronze.yellow_trips) "
        "- (SELECT count(*) FROM silver.yellow_trips_clean) "
        "- (SELECT count(*) FROM silver.yellow_trips_rejected))"
    ),
    "pickup_zones_resolved": "SELECT count(*) FROM gold.mart_zone_revenue WHERE pickup_zone = 'Unknown'",
    "gold_marts_have_rows": (
        "SELECT CASE WHEN (SELECT count(*) FROM gold.mart_hourly_demand) > 0 "
        "AND (SELECT count(*) FROM gold.mart_zone_revenue) > 0 "
        "AND (SELECT count(*) FROM gold.mart_airport_trips) > 0 THEN 0 ELSE 1 END"
    ),
}


def run_checks(
    db_path: Path = DB_PATH,
    report_path: Path = REPORT_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Warehouse not found: {db_path}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[str, int]] = []

    with duckdb.connect(str(db_path), read_only=True) as con:
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
        metrics_row = con.execute(
            """
            SELECT raw_rows, clean_rows, rejected_rows, acceptance_rate_pct,
                   pickup_zones, airport_trips, gross_revenue
            FROM gold.pipeline_run_summary
            """
        ).fetchone()

    generated_at = datetime.now(UTC).isoformat()
    metric_names = [
        "raw_rows",
        "clean_rows",
        "rejected_rows",
        "acceptance_rate_pct",
        "pickup_zones",
        "airport_trips",
        "gross_revenue",
    ]
    metrics = dict(zip(metric_names, metrics_row, strict=True))
    payload = {
        "generated_at": generated_at,
        "status": "FAIL" if failures else "PASS",
        "checks": [
            {"name": name, "status": status, "failed_rows": failed_rows}
            for name, status, failed_rows in rows
        ],
        "metrics": metrics,
        "mart_row_counts": {table: count for table, count in mart_counts},
    }

    lines = [
        "# Data Quality Report",
        "",
        f"Generated at: `{generated_at}`",
        "",
        f"Overall status: **{payload['status']}**",
        "",
        "| Check | Status | Failed Rows |",
        "|---|---:|---:|",
    ]
    lines += [f"| {name} | {status} | {failed_rows} |" for name, status, failed_rows in rows]
    lines += ["", "## Mart Row Counts", "", "| Table | Rows |", "|---|---:|"]
    lines += [f"| {table} | {count} |" for table, count in mart_counts]
    lines += ["", "## Pipeline Metrics", "", "| Metric | Value |", "|---|---:|"]
    lines += [f"| {name} | {value} |" for name, value in metrics.items()]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_report_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Wrote {json_report_path}")

    if failures:
        for name, failed_rows in failures:
            print(f"FAIL {name}: {failed_rows}")
        raise SystemExit(1)
    print("All data quality checks passed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate NYC taxi lakehouse contracts.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument("--json-report-path", type=Path, default=JSON_REPORT_PATH)
    args = parser.parse_args()
    run_checks(args.db_path, args.report_path, args.json_report_path)


if __name__ == "__main__":
    main()
