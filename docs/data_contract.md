# Data Contract

## Source

NYC TLC yellow taxi trip records are loaded as monthly Parquet files. The raw
zone keeps files in their original column layout so schema changes are isolated
from curated consumers.

## Grain

`silver.yellow_trips_clean` has one row per taxi trip.

## Critical Fields

| Field | Rule |
|---|---|
| `pickup_at` | Not null |
| `dropoff_at` | Not null and later than pickup |
| `trip_distance` | Between 0.1 and 100 miles |
| `total_amount` | Between 0 and 1000 USD |
| `pickup_location_id` | Not null |
| `dropoff_location_id` | Not null |

## Gold Marts

| Mart | Purpose |
|---|---|
| `gold.mart_hourly_demand` | Demand, passenger, distance, duration and revenue by pickup hour |
| `gold.mart_zone_revenue` | Pickup zone revenue leaderboard |
| `gold.mart_airport_trips` | Airport trip volume, revenue and tip behavior |
