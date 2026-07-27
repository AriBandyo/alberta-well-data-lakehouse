# Public snapshot data dictionary

## Source columns

| Column | Type | Meaning |
|---|---|---|
| municipality | string | Alberta municipality published by the source |
| year | integer | Reference year for the published value |
| metric | string | oil_production, natural_gas_production, or well_count |
| value | number | Published metric value |
| unit | string | m3 for production or count for wells |
| yoy_change_pct | decimal | Published year-over-year percentage change |
| five_year_change_pct | decimal | Published five-year percentage change |
| source_name | string | Publishing organization or product |
| source_url | string | Row-level source page |
| source_last_updated | date | Date displayed by the source |
| licence | string | Licence attached to the source dataset |
| snapshot_retrieved_at | date | Date this repository snapshot was assembled |

## Gold mart columns

`mart_municipality_energy_summary` combines the three source datasets using a deterministic municipality key. It contains oil and gas volumes, well counts, published growth rates, derived prior-period estimates, per-reported-well comparisons, an activity classification, and a 0-100 energy activity score.

Prior-period columns ending in `_estimated` are calculated from the current published value and percentage change. They are not separately sourced observations.
