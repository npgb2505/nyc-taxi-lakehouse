from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local NYC taxi lakehouse demo.")
    parser.add_argument("--rows", type=int, default=500)
    args = parser.parse_args()

    run(["scripts/generate_sample_data.py", "--rows", str(args.rows)])
    run(["scripts/build_lakehouse.py"])
    run(["scripts/data_quality.py"])


if __name__ == "__main__":
    main()
