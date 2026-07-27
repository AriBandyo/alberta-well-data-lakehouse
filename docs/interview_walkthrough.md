# Interview walkthrough

## Problem

Public Alberta energy data is available through multiple products and formats. Analysts need consistent identifiers, quality controls, reproducible transformations, and business-ready outputs rather than disconnected source files.

## Solution

The project implements a versioned public-data pipeline with bronze, silver, and gold layers. It preserves source lineage, creates stable municipality identifiers, validates incoming values, reconciles oil, natural gas, and well-count metrics, and publishes SQL- and Tableau-ready outputs.

## Design decisions

- A small official snapshot is committed so reviewers can run the project without network access.
- Large AER and Petrinex downloads are handled through adapters and excluded from Git.
- Source metadata remains attached to every row for traceability.
- Quality checks run before analytical outputs are produced.
- The default path uses Pandas and SQLite for portability; the same source data can run through PySpark and Delta Lake.
- Prior-period estimates are named explicitly to distinguish calculations from sourced observations.

## Results

The included run processed 33 source records across 18 municipalities, passed 18 quality checks, and produced dimension, fact, and summary tables. It also created a queryable database, dashboard extracts, ranked results, charts, and a documented analysis.

## Scaling path

For full ST37 and Petrinex files, the same architecture can be extended with partitioned Delta tables, incremental source manifests, file-level watermarks, schema-evolution alerts, and dbt models over Parquet or a cloud warehouse.
