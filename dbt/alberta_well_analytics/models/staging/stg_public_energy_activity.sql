with source as (
    select * from read_csv_auto('{{ env_var("PUBLIC_FACT_CSV") }}', header = true)
)
select
    municipality_key,
    trim(municipality) as municipality,
    cast(year as integer) as year,
    metric,
    cast(value as double) as value,
    unit,
    cast(yoy_change_pct as double) as yoy_change_pct,
    cast(five_year_change_pct as double) as five_year_change_pct
from source
