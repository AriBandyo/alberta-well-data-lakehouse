select
    municipality_key,
    municipality,
    metric,
    year,
    value,
    yoy_change_pct,
    dense_rank() over (partition by metric order by value desc) as snapshot_rank
from {{ ref('stg_public_energy_activity') }}
