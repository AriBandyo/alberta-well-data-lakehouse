# Architecture

## Default execution path

1. Versioned official CSV files are read from `data/source_snapshot`.
2. Bronze ingestion preserves every source field and adds source filename, ingestion timestamp, and SHA-256 record hash.
3. Data-quality checks run before transformations.
4. Silver processing standardizes municipality names, stable municipality keys, numeric types, dates, and duplicate handling.
5. Gold processing builds a municipality dimension, a normalized energy activity fact table, and a municipality summary mart.
6. Serving outputs are written to CSV, optional Parquet, SQLite, Tableau extracts, result tables, charts, and a local dashboard.

## Optional Spark path

`public_spark.py` applies an explicit schema, reads all official snapshot files into a unified DataFrame, and writes bronze and silver Delta tables. Delta merge keys are municipality key, year, and metric. The silver Delta table is exported as Parquet for downstream transformation.

## Orchestration

Dagster represents the source snapshot, quality checks, and gold analytics marts as assets. The schedule uses the America/Edmonton timezone.

## Failure handling

Blocking data-quality failures stop the pipeline before gold tables are built. Download commands use streamed writes, temporary `.part` files, retries, exponential backoff, timeouts, and HTTP status validation.
