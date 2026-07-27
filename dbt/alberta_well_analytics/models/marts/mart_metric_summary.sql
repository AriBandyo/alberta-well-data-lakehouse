select
    metric,
    year,
    count(*) as source_records,
    count(distinct municipality_key) as municipalities,
    sum(value) as snapshot_total,
    avg(yoy_change_pct) as average_yoy_change_pct,
    avg(five_year_change_pct) as average_five_year_change_pct
from {{ ref('stg_public_energy_activity') }}
group by metric, year
