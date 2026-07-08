select
    pickup_date,
    pickup_hour,
    pickup_day_name,
    count(*) as trips,
    sum(passenger_count) as passengers,
    round(avg(duration_minutes), 2) as avg_duration_minutes,
    round(avg(trip_distance), 2) as avg_trip_distance,
    round(sum(total_amount), 2) as gross_revenue
from {{ ref('int_trip_enriched') }}
group by 1, 2, 3
