from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "municipality", "year", "metric", "value", "unit", "yoy_change_pct",
    "five_year_change_pct", "source_name", "source_url", "source_last_updated",
    "licence", "snapshot_retrieved_at",
}


@dataclass(frozen=True)
class PublicPaths:
    root: Path
    source: Path
    bronze: Path
    silver: Path
    gold: Path
    tableau: Path
    results: Path
    database: Path

    @classmethod
    def from_root(cls, root: Path) -> "PublicPaths":
        root = root.resolve()
        return cls(
            root=root,
            source=root / "data" / "source_snapshot",
            bronze=root / "lakehouse" / "bronze" / "public_snapshot",
            silver=root / "lakehouse" / "silver" / "public_snapshot",
            gold=root / "warehouse" / "gold",
            tableau=root / "tableau" / "data",
            results=root / "results",
            database=root / "warehouse" / "alberta_energy_analytics.sqlite",
        )

    def ensure(self) -> None:
        for path in (self.bronze, self.silver, self.gold, self.tableau, self.results, self.database.parent):
            path.mkdir(parents=True, exist_ok=True)


def municipality_key(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def _load_one(path: Path, expected_metric: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    if set(frame["metric"].dropna().unique()) != {expected_metric}:
        raise ValueError(f"{path.name} contains an unexpected metric")
    source_hash_input = frame[list(sorted(REQUIRED_COLUMNS))].astype(str).agg("|".join, axis=1)
    frame["record_hash"] = source_hash_input.map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )
    frame["source_file"] = path.name
    frame["ingested_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    return frame


def load_bronze(paths: PublicPaths) -> dict[str, pd.DataFrame]:
    paths.ensure()
    datasets = {
        "oil": _load_one(paths.source / "oil_production_by_municipality_2025.csv", "oil_production"),
        "gas": _load_one(paths.source / "natural_gas_production_by_municipality_2025.csv", "natural_gas_production"),
        "wells": _load_one(paths.source / "well_count_by_municipality_2024.csv", "well_count"),
    }
    for name, frame in datasets.items():
        frame.to_csv(paths.bronze / f"{name}.csv", index=False)
    return datasets


def quality_report(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks: list[dict[str, Any]] = []

    def add(dataset: str, check_name: str, failed_rows: int, severity: str = "ERROR") -> None:
        checks.append({
            "dataset": dataset,
            "check_name": check_name,
            "status": "PASS" if int(failed_rows) == 0 else "FAIL",
            "failed_rows": int(failed_rows),
            "severity": severity,
        })

    for name, frame in datasets.items():
        add(name, "required_fields_not_null", int(frame[list(REQUIRED_COLUMNS)].isna().any(axis=1).sum()))
        add(name, "municipality_year_unique", int(frame.duplicated(["municipality", "year", "metric"]).sum()))
        add(name, "value_non_negative", int((pd.to_numeric(frame["value"], errors="coerce") < 0).sum()))
        add(name, "year_in_expected_range", int((~pd.to_numeric(frame["year"], errors="coerce").between(2000, 2100)).sum()))
        add(name, "source_url_is_https", int((~frame["source_url"].astype(str).str.startswith("https://")).sum()))
        add(name, "licence_present", int(frame["licence"].astype(str).str.strip().eq("").sum()))
    return pd.DataFrame(checks)


def _standardize(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["municipality"] = result["municipality"].astype(str).str.strip()
    result["municipality_key"] = result["municipality"].map(municipality_key)
    result["year"] = pd.to_numeric(result["year"], errors="raise").astype("int64")
    result["value"] = pd.to_numeric(result["value"], errors="raise").astype("float64")
    result["yoy_change_pct"] = pd.to_numeric(result["yoy_change_pct"], errors="coerce")
    result["five_year_change_pct"] = pd.to_numeric(result["five_year_change_pct"], errors="coerce")
    result["source_last_updated"] = pd.to_datetime(result["source_last_updated"], errors="raise").dt.date.astype(str)
    result["snapshot_retrieved_at"] = pd.to_datetime(result["snapshot_retrieved_at"], errors="raise").dt.date.astype(str)
    return result.sort_values(["municipality", "year"]).drop_duplicates(
        ["municipality", "year", "metric"], keep="last"
    )


def build_silver(paths: PublicPaths, bronze: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    silver = {name: _standardize(frame) for name, frame in bronze.items()}
    for name, frame in silver.items():
        frame.to_csv(paths.silver / f"{name}.csv", index=False)
    return silver


def _safe_prior(current: pd.Series, percent: pd.Series) -> pd.Series:
    denominator = 1 + percent / 100.0
    return current.where(denominator.eq(0), current / denominator)


def build_gold(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    oil = silver["oil"].rename(columns={
        "value": "oil_m3_2025", "yoy_change_pct": "oil_yoy_pct",
        "five_year_change_pct": "oil_five_year_pct", "year": "oil_year",
    })[["municipality_key", "municipality", "oil_year", "oil_m3_2025", "oil_yoy_pct", "oil_five_year_pct"]]
    gas = silver["gas"].rename(columns={
        "value": "gas_m3_2025", "yoy_change_pct": "gas_yoy_pct",
        "five_year_change_pct": "gas_five_year_pct", "year": "gas_year",
    })[["municipality_key", "municipality", "gas_year", "gas_m3_2025", "gas_yoy_pct", "gas_five_year_pct"]]
    wells = silver["wells"].rename(columns={
        "value": "well_count_2024", "yoy_change_pct": "well_count_yoy_pct",
        "five_year_change_pct": "well_count_five_year_pct", "year": "well_count_year",
    })[["municipality_key", "municipality", "well_count_year", "well_count_2024", "well_count_yoy_pct", "well_count_five_year_pct"]]

    dim = pd.concat([
        oil[["municipality_key", "municipality"]],
        gas[["municipality_key", "municipality"]],
        wells[["municipality_key", "municipality"]],
    ]).drop_duplicates("municipality_key").sort_values("municipality")

    summary = dim.merge(oil.drop(columns="municipality"), on="municipality_key", how="left")
    summary = summary.merge(gas.drop(columns="municipality"), on="municipality_key", how="left")
    summary = summary.merge(wells.drop(columns="municipality"), on="municipality_key", how="left")

    for column in ["oil_m3_2025", "gas_m3_2025", "well_count_2024"]:
        summary[column] = summary[column].fillna(0.0)
    summary["oil_m3_2024_estimated"] = _safe_prior(summary["oil_m3_2025"], summary["oil_yoy_pct"])
    summary["gas_m3_2024_estimated"] = _safe_prior(summary["gas_m3_2025"], summary["gas_yoy_pct"])
    summary["oil_m3_2020_estimated"] = _safe_prior(summary["oil_m3_2025"], summary["oil_five_year_pct"])
    summary["gas_m3_2020_estimated"] = _safe_prior(summary["gas_m3_2025"], summary["gas_five_year_pct"])
    summary["oil_m3_per_reported_well"] = summary["oil_m3_2025"].where(summary["well_count_2024"].gt(0)) / summary["well_count_2024"].where(summary["well_count_2024"].gt(0))
    summary["gas_m3_per_reported_well"] = summary["gas_m3_2025"].where(summary["well_count_2024"].gt(0)) / summary["well_count_2024"].where(summary["well_count_2024"].gt(0))
    summary["combined_yoy_pct"] = summary[["oil_yoy_pct", "gas_yoy_pct"]].mean(axis=1, skipna=True)
    summary["activity_class"] = pd.cut(
        summary["combined_yoy_pct"], bins=[-math.inf, -5, 5, math.inf],
        labels=["Declining", "Stable", "Expanding"], include_lowest=True,
    ).astype("string").fillna("Not comparable")

    def minmax_log(series: pd.Series) -> pd.Series:
        logged = series.fillna(0).clip(lower=0).map(math.log1p)
        spread = logged.max() - logged.min()
        return pd.Series(0.0, index=series.index) if spread == 0 else (logged - logged.min()) / spread

    summary["energy_activity_score"] = (
        45 * minmax_log(summary["oil_m3_2025"])
        + 35 * minmax_log(summary["gas_m3_2025"])
        + 20 * minmax_log(summary["well_count_2024"])
    ).round(2)
    summary = summary.sort_values(["energy_activity_score", "municipality"], ascending=[False, True])

    fact = pd.concat([
        silver["oil"][["municipality_key", "municipality", "year", "metric", "value", "unit", "yoy_change_pct", "five_year_change_pct"]],
        silver["gas"][["municipality_key", "municipality", "year", "metric", "value", "unit", "yoy_change_pct", "five_year_change_pct"]],
        silver["wells"][["municipality_key", "municipality", "year", "metric", "value", "unit", "yoy_change_pct", "five_year_change_pct"]],
    ], ignore_index=True).sort_values(["metric", "value"], ascending=[True, False])

    return {
        "dim_municipality": dim.reset_index(drop=True),
        "fct_energy_activity": fact.reset_index(drop=True),
        "mart_municipality_energy_summary": summary.reset_index(drop=True),
    }


def write_database(paths: PublicPaths, tables: dict[str, pd.DataFrame]) -> None:
    if paths.database.exists():
        paths.database.unlink()
    with sqlite3.connect(paths.database) as connection:
        for name, frame in tables.items():
            frame.to_sql(name, connection, index=False, if_exists="replace")
        connection.execute("CREATE INDEX idx_fact_municipality ON fct_energy_activity(municipality_key)")
        connection.execute("CREATE INDEX idx_summary_score ON mart_municipality_energy_summary(energy_activity_score)")


def _try_parquet(path: Path, frame: pd.DataFrame) -> bool:
    try:
        frame.to_parquet(path, index=False)
        return True
    except ImportError:
        return False


def write_outputs(paths: PublicPaths, tables: dict[str, pd.DataFrame], quality: pd.DataFrame) -> dict[str, Any]:
    paths.ensure()
    parquet_written = True
    for name, frame in tables.items():
        frame.to_csv(paths.gold / f"{name}.csv", index=False)
        parquet_written = _try_parquet(paths.gold / f"{name}.parquet", frame) and parquet_written

    summary = tables["mart_municipality_energy_summary"]
    fact = tables["fct_energy_activity"]
    summary.to_csv(paths.tableau / "public_municipality_energy_summary.csv", index=False)
    fact[fact["metric"].eq("oil_production")].to_csv(paths.tableau / "public_oil_production_2025.csv", index=False)
    fact[fact["metric"].eq("natural_gas_production")].to_csv(paths.tableau / "public_natural_gas_production_2025.csv", index=False)
    fact[fact["metric"].eq("well_count")].to_csv(paths.tableau / "public_well_count_2024.csv", index=False)
    quality.to_csv(paths.tableau / "data_quality_report.csv", index=False)
    quality.to_csv(paths.results / "data_quality_report.csv", index=False)

    summary.nlargest(10, "oil_m3_2025")[["municipality", "oil_m3_2025", "oil_yoy_pct", "oil_five_year_pct"]].to_csv(paths.results / "top_oil_producers.csv", index=False)
    summary.nlargest(10, "gas_m3_2025")[["municipality", "gas_m3_2025", "gas_yoy_pct", "gas_five_year_pct"]].to_csv(paths.results / "top_gas_producers.csv", index=False)
    summary.nlargest(10, "well_count_2024")[["municipality", "well_count_2024", "well_count_yoy_pct", "well_count_five_year_pct"]].to_csv(paths.results / "top_well_activity.csv", index=False)

    metrics = {
        "source_records": int(len(fact)),
        "municipalities": int(summary["municipality_key"].nunique()),
        "oil_records": int(fact["metric"].eq("oil_production").sum()),
        "gas_records": int(fact["metric"].eq("natural_gas_production").sum()),
        "well_count_records": int(fact["metric"].eq("well_count").sum()),
        "snapshot_oil_m3": float(summary["oil_m3_2025"].sum()),
        "snapshot_gas_m3": float(summary["gas_m3_2025"].sum()),
        "snapshot_reported_wells": int(summary["well_count_2024"].sum()),
        "quality_checks": int(len(quality)),
        "quality_failures": int(quality["status"].eq("FAIL").sum()),
        "top_oil_municipality": str(summary.nlargest(1, "oil_m3_2025").iloc[0]["municipality"]),
        "top_gas_municipality": str(summary.nlargest(1, "gas_m3_2025").iloc[0]["municipality"]),
        "top_well_count_municipality": str(summary.nlargest(1, "well_count_2024").iloc[0]["municipality"]),
        "parquet_written": parquet_written,
        "database_path": str(paths.database.relative_to(paths.root)),
    }
    (paths.results / "summary_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    run_manifest = {
        "source_files": sorted(path.name for path in paths.source.glob("*.csv")),
        "bronze_tables": sorted(path.name for path in paths.bronze.glob("*.csv")),
        "silver_tables": sorted(path.name for path in paths.silver.glob("*.csv")),
        "gold_tables": sorted(path.name for path in paths.gold.glob("*.csv")),
        "serving_database": str(paths.database.relative_to(paths.root)),
        "tableau_extracts": sorted(path.name for path in paths.tableau.glob("*.csv")),
        "result_files": sorted(path.name for path in paths.results.glob("*.*")),
        "row_counts": {name: int(len(frame)) for name, frame in tables.items()},
        "quality_checks": int(len(quality)),
        "quality_failures": int(quality["status"].eq("FAIL").sum()),
    }
    (paths.results / "pipeline_run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2), encoding="utf-8"
    )
    return metrics


def run_public_pipeline(root: Path) -> dict[str, Any]:
    paths = PublicPaths.from_root(root)
    bronze = load_bronze(paths)
    quality = quality_report(bronze)
    if quality.query("status == 'FAIL' and severity == 'ERROR'").shape[0]:
        raise ValueError("Blocking data-quality checks failed; review results/data_quality_report.csv")
    silver = build_silver(paths, bronze)
    gold = build_gold(silver)
    write_database(paths, gold)
    return write_outputs(paths, gold, quality)
