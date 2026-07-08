select
    pickup_date,
    pickup_borough,
    pickup_zone,
    count(*) as airport_trips,
    round(sum(total_amount), 2) as airport_revenue,
    round(avg(tip_rate), 4) as avg_tip_rate,
    round(avg(duration_minutes), 2) as avg_duration_minutes
from {{ ref('int_trip_enriched') }}
where is_airport_trip = 1
group by 1, 2, 3
