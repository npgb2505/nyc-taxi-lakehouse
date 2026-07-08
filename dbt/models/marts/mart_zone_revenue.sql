select
    pickup_borough,
    pickup_zone,
    count(*) as trips,
    round(sum(total_amount), 2) as gross_revenue,
    round(sum(tip_amount), 2) as tips,
    round(avg(trip_distance), 2) as avg_trip_distance,
    round(avg(total_amount), 2) as avg_ticket
from {{ ref('int_trip_enriched') }}
group by 1, 2
