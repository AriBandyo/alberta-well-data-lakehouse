# Public data sources

## Bundled official snapshot

The repository includes a curated municipality-level snapshot from the Government of Alberta Regional Dashboard under the Open Government Licence - Alberta. Every row contains the upstream page URL, source update date, retrieval date, metric, unit, and published change rates.

Included files:

- `oil_production_by_municipality_2025.csv`
- `natural_gas_production_by_municipality_2025.csv`
- `well_count_by_municipality_2024.csv`

The snapshot is intentionally small enough to review in Git while still being real public data. It is not a complete provincial extract.

## Full free sources supported by the project

### AER ST37

The Alberta Energy Regulator publishes the List of Wells in Alberta monthly. An official ArcGIS feature service also provides queryable point features with well type, category, surface location, status symbol, and geometry; the downloader can retrieve a review-sized GeoJSON sample. The source includes surface-hole, bottom-hole, production-string, and geometry information in Excel and spatial packages. The repository contains a downloader configuration but does not redistribute the large source archive.

### Petrinex Alberta Public Data

The Petrinex public portal provides monthly infrastructure and volumetric extracts, including Well Infrastructure, Well Licence, Facility Infrastructure, Facility Operator History, Well-to-Facility Link, and Conventional Volumetric Data. API URL templates are configured in `.env` and implemented in `scripts/download_free_sources.py`.

## Licensing and redistribution

Preserve source attribution and review each upstream source's terms before redistributing a full downloaded extract. The bundled Regional Dashboard rows retain source URLs and licence metadata. Large AER and Petrinex files belong in `data/external/`, which is excluded from Git.
