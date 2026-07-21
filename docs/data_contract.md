# NYC Taxi Data Contract

## Ownership and service expectations

| Item | Definition |
|---|---|
| Producer | NYC Taxi & Limousine Commission trip-record files |
| Pipeline owner | Nguyen Phuc Gia Bao |
| Refresh | Monthly in official-data mode; on demand in demo mode |
| Raw format | Parquet partitioned by trip type, year, and month |
| Curated grain | One accepted row per taxi trip |
| Failure policy | Quarantine invalid rows; fail release when reconciliation or curated checks fail |

## Required source fields

| Source field | Curated rule |
|---|---|
| `tpep_pickup_datetime` | Required |
| `tpep_dropoff_datetime` | Required, after pickup, duration at most 360 minutes |
| `trip_distance` | Between 0.1 and 100 miles |
| `fare_amount` | Non-negative |
| `total_amount` | Between 0 and 1000 USD |
| `PULocationID` | Required and expected in taxi-zone reference data |
| `DOLocationID` | Required |

A row that violates one or more rules is written to `silver.yellow_trips_rejected`. The semicolon-delimited `rejection_reason` retains every rule violated by that row.

## Reconciliation invariant

```text
count(bronze.yellow_trips)
  = count(silver.yellow_trips_clean)
  + count(silver.yellow_trips_rejected)
```

The data-quality command exits non-zero if this invariant fails.

## Published data products

| Mart | Grain | Primary measures |
|---|---|---|
| `gold.mart_hourly_demand` | Pickup date and hour | trips, passengers, duration, distance, revenue |
| `gold.mart_zone_revenue` | Pickup borough and zone | trips, revenue, tips, distance, average ticket |
| `gold.mart_airport_trips` | Pickup date | airport trips, revenue, tip rate, duration |
| `gold.pipeline_run_summary` | Pipeline execution | raw, clean, rejected, acceptance rate, coverage |

## Schema evolution

Bronze reads Parquet with `union_by_name = true` so additive source columns do not break historical files. Curated SQL explicitly selects and casts contracted fields; incompatible type or field changes therefore fail during build instead of silently changing downstream schemas.
