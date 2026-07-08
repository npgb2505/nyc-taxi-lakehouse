from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "taxi_lakehouse.duckdb"


def test_demo_pipeline_builds_gold_marts() -> None:
    subprocess.run([sys.executable, "scripts/run_demo.py", "--rows", "120"], cwd=ROOT, check=True)

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        hourly_rows = con.execute("SELECT count(*) FROM gold.mart_hourly_demand").fetchone()[0]
        zone_rows = con.execute("SELECT count(*) FROM gold.mart_zone_revenue").fetchone()[0]
        airport_rows = con.execute("SELECT count(*) FROM gold.mart_airport_trips").fetchone()[0]
        revenue = con.execute("SELECT sum(gross_revenue) FROM gold.mart_hourly_demand").fetchone()[0]

    assert hourly_rows > 0
    assert zone_rows > 0
    assert airport_rows > 0
    assert revenue > 0
