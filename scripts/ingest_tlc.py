from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def download_file(url: str, target: Path, force: bool = False) -> None:
    if target.exists() and target.stat().st_size > 0 and not force:
        print(f"Already downloaded: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    retry = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    with session.get(url, stream=True, timeout=(10, 120)) as response:
        response.raise_for_status()
        with temporary.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file is empty: {url}")
    os.replace(temporary, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NYC TLC trip parquet files.")
    parser.add_argument("--trip-type", default="yellow", choices=["yellow", "green", "fhvhv"])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, choices=range(1, 13), metavar="1-12", required=True)
    parser.add_argument("--force", action="store_true", help="Replace a file that has already been downloaded.")
    args = parser.parse_args()

    month = f"{args.month:02d}"
    file_name = f"{args.trip_type}_tripdata_{args.year}-{month}.parquet"
    url = f"{BASE_URL}/{file_name}"
    target = ROOT / "data" / "raw" / args.trip_type / f"year={args.year}" / f"month={month}" / file_name
    print(f"Downloading {url}")
    download_file(url, target, force=args.force)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
