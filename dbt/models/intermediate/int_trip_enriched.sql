select
    t.*,
    coalesce(pu.Borough, 'Unknown') as pickup_borough,
    coalesce(pu.Zone, 'Unknown') as pickup_zone,
    coalesce(doz.Borough, 'Unknown') as dropoff_borough,
    coalesce(doz.Zone, 'Unknown') as dropoff_zone,
    case
        when t.payment_type = 1 then 'Credit card'
        when t.payment_type = 2 then 'Cash'
        else 'Other'
    end as payment_method,
    round(t.tip_amount / nullif(t.total_amount, 0), 4) as tip_rate
from {{ ref('stg_yellow_trips') }} t
left join bronze.taxi_zones pu
    on t.pickup_location_id = pu.LocationID
left join bronze.taxi_zones doz
    on t.dropoff_location_id = doz.LocationID
