from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from scripts.generate_sample_data import build_trips

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "taxi_lakehouse.duckdb"


def test_demo_pipeline_builds_gold_marts() -> None:
    subprocess.run(
        [sys.executable, "scripts/run_demo.py", "--rows", "120", "--invalid-rows", "4"],
        cwd=ROOT,
        check=True,
    )

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        hourly_rows = con.execute("SELECT count(*) FROM gold.mart_hourly_demand").fetchone()[0]
        zone_rows = con.execute("SELECT count(*) FROM gold.mart_zone_revenue").fetchone()[0]
        airport_rows = con.execute("SELECT count(*) FROM gold.mart_airport_trips").fetchone()[0]
        revenue = con.execute("SELECT sum(gross_revenue) FROM gold.mart_hourly_demand").fetchone()[0]
        raw_rows, clean_rows, rejected_rows = con.execute(
            "SELECT raw_rows, clean_rows, rejected_rows FROM gold.pipeline_run_summary"
        ).fetchone()
        rejection_reasons = con.execute(
            "SELECT count(DISTINCT rejection_reason) FROM silver.yellow_trips_rejected"
        ).fetchone()[0]

    assert hourly_rows > 0
    assert zone_rows > 0
    assert airport_rows > 0
    assert revenue > 0
    assert (raw_rows, clean_rows, rejected_rows) == (120, 116, 4)
    assert rejection_reasons == 4


def test_sample_generator_is_deterministic_and_validates_arguments() -> None:
    first = build_trips(12, invalid_rows=2)
    second = build_trips(12, invalid_rows=2)
    assert first.equals(second)
    assert first.loc[0, "trip_distance"] == -1.0
    assert first.loc[1, "tpep_dropoff_datetime"] == first.loc[1, "tpep_pickup_datetime"]
    with pytest.raises(ValueError):
        build_trips(3, invalid_rows=4)
