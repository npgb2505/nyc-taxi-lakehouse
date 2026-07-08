from __future__ import annotations

import argparse
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with target.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NYC TLC trip parquet files.")
    parser.add_argument("--trip-type", default="yellow", choices=["yellow", "green", "fhvhv"])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    args = parser.parse_args()

    month = f"{args.month:02d}"
    file_name = f"{args.trip_type}_tripdata_{args.year}-{month}.parquet"
    url = f"{BASE_URL}/{file_name}"
    target = ROOT / "data" / "raw" / args.trip_type / f"year={args.year}" / f"month={month}" / file_name
    print(f"Downloading {url}")
    download_file(url, target)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
