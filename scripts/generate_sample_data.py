from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def build_trips(rows: int) -> pd.DataFrame:
    pickup_start = pd.Timestamp("2024-01-01 00:00:00")
    records = []
    pu_locations = [132, 138, 161, 162, 230, 236, 237, 238, 239, 261]
    do_locations = [48, 68, 79, 87, 90, 100, 114, 186, 234, 263]

    for i in range(rows):
        pickup = pickup_start + pd.Timedelta(minutes=17 * i)
        duration = 6 + (i % 55)
        distance = round(0.7 + (i % 34) * 0.42, 2)
        fare = round(3.0 + distance * 3.1 + duration * 0.22, 2)
        tip = round(fare * ([0.0, 0.08, 0.12, 0.18, 0.22][i % 5]), 2)
        tolls = 6.94 if i % 19 == 0 else 0.0
        airport_fee = 1.75 if pu_locations[i % len(pu_locations)] in {132, 138} else 0.0
        total = round(fare + 1.0 + 0.5 + tip + tolls + 1.0 + 2.5 + airport_fee, 2)
        records.append(
            {
                "VendorID": 1 + (i % 2),
                "tpep_pickup_datetime": pickup,
                "tpep_dropoff_datetime": pickup + pd.Timedelta(minutes=duration),
                "passenger_count": 1 + (i % 4),
                "trip_distance": distance,
                "RatecodeID": 2 if airport_fee else 1,
                "store_and_fwd_flag": "N",
                "PULocationID": pu_locations[i % len(pu_locations)],
                "DOLocationID": do_locations[i % len(do_locations)],
                "payment_type": 1 if i % 7 else 2,
                "fare_amount": fare,
                "extra": 1.0,
                "mta_tax": 0.5,
                "tip_amount": tip,
                "tolls_amount": tolls,
                "improvement_surcharge": 1.0,
                "total_amount": total,
                "congestion_surcharge": 2.5,
                "Airport_fee": airport_fee,
            }
        )
    return pd.DataFrame(records)


def build_zones() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (48, "Manhattan", "Clinton East", "Yellow Zone"),
            (68, "Manhattan", "East Chelsea", "Yellow Zone"),
            (79, "Manhattan", "East Village", "Yellow Zone"),
            (87, "Manhattan", "Financial District North", "Yellow Zone"),
            (90, "Manhattan", "Flatiron", "Yellow Zone"),
            (100, "Manhattan", "Garment District", "Yellow Zone"),
            (114, "Manhattan", "Greenwich Village South", "Yellow Zone"),
            (132, "Queens", "JFK Airport", "Airports"),
            (138, "Queens", "LaGuardia Airport", "Airports"),
            (161, "Manhattan", "Midtown Center", "Yellow Zone"),
            (162, "Manhattan", "Midtown East", "Yellow Zone"),
            (186, "Manhattan", "Penn Station/Madison Sq West", "Yellow Zone"),
            (230, "Manhattan", "Times Sq/Theatre District", "Yellow Zone"),
            (234, "Manhattan", "Union Sq", "Yellow Zone"),
            (236, "Manhattan", "Upper East Side North", "Yellow Zone"),
            (237, "Manhattan", "Upper East Side South", "Yellow Zone"),
            (238, "Manhattan", "Upper West Side North", "Yellow Zone"),
            (239, "Manhattan", "Upper West Side South", "Yellow Zone"),
            (261, "Manhattan", "World Trade Center", "Yellow Zone"),
            (263, "Manhattan", "Yorkville West", "Yellow Zone"),
        ],
        columns=["LocationID", "Borough", "Zone", "service_zone"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic sample NYC taxi data.")
    parser.add_argument("--rows", type=int, default=500)
    args = parser.parse_args()

    raw_dir = ROOT / "data" / "raw" / "yellow" / "year=2024" / "month=01"
    ref_dir = ROOT / "data" / "raw" / "reference"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ref_dir.mkdir(parents=True, exist_ok=True)

    trips_path = raw_dir / "yellow_tripdata_2024-01.parquet"
    zones_path = ref_dir / "taxi_zone_lookup.csv"
    build_trips(args.rows).to_parquet(trips_path, index=False)
    build_zones().to_csv(zones_path, index=False)

    print(f"Wrote {trips_path}")
    print(f"Wrote {zones_path}")


if __name__ == "__main__":
    main()
