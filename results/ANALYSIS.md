# Actual output and findings

The pipeline processed 33 official public-data records covering 18 distinct Alberta municipalities. All 18 automated data-quality checks passed with 0 failures.

## Snapshot totals

- Oil production represented in the included 2025 snapshot: 50.38M m³
- Natural gas production represented in the included 2025 snapshot: 2.65B m³
- Wells represented in the included 2024 well-count snapshot: 1,826

These are totals for the curated municipalities included in this repository, not province-wide totals.

## Leading municipalities

### Oil production
- Bonnyville No. 87: 32.50M m³
- Lesser Slave River No. 124: 6.30M m³
- Greenview No. 16: 5.20M m³

### Natural gas production
- Rocky View County: 1.70B m³
- Special Area No. 4: 293.60M m³
- Fairview No. 136: 252.30M m³

## Production momentum

The momentum measure averages the available oil and natural-gas year-over-year changes. It is used only when at least one production measure is available.

### Strongest growth
- Rocky View County: 20%
- Lesser Slave River No. 124: 15%
- Greenview No. 16: 12%

### Largest declines
- Acadia No. 34: -30%
- Special Area No. 4: -24%
- Peace No. 135: -23%

## Generated assets

- Bronze and silver CSV tables with ingestion metadata and standardized municipality keys
- Gold dimension, fact, and municipality summary tables in CSV and Parquet when PyArrow is installed
- A queryable SQLite analytics database at `warehouse/alberta_energy_analytics.sqlite`
- Tableau-ready CSV extracts and a local browser dashboard
- Ranked result tables, quality results, charts, and this analysis

## Interpretation limits

Oil and gas values use 2025 data, while well counts use 2024 data. Per-well ratios are therefore indicative comparisons, not engineering productivity measures. Prior-year and five-year baseline columns are mathematically derived from the published percentage changes and are clearly named as estimates.
