from __future__ import annotations

from pathlib import Path

from dagster import AssetExecutionContext, Definitions, ScheduleDefinition, asset, define_asset_job

from alberta_well_lakehouse.public_data import PublicPaths, load_bronze, quality_report, run_public_pipeline

ROOT = Path(__file__).resolve().parents[1]


@asset(group_name="official_source", compute_kind="csv")
def official_public_snapshot(context: AssetExecutionContext) -> dict[str, int]:
    datasets = load_bronze(PublicPaths.from_root(ROOT))
    counts = {name: len(frame) for name, frame in datasets.items()}
    context.log.info("Official source rows: %s", counts)
    return counts


@asset(deps=[official_public_snapshot], group_name="quality", compute_kind="pandas")
def public_data_quality(context: AssetExecutionContext) -> dict[str, int]:
    paths = PublicPaths.from_root(ROOT)
    report = quality_report(load_bronze(paths))
    result = {"checks": len(report), "failures": int(report["status"].eq("FAIL").sum())}
    context.log.info("Quality result: %s", result)
    return result


@asset(deps=[public_data_quality], group_name="gold", compute_kind="pandas/sqlite")
def municipality_energy_marts(context: AssetExecutionContext) -> dict[str, object]:
    result = run_public_pipeline(ROOT)
    context.log.info("Pipeline metrics: %s", result)
    return result


daily_job = define_asset_job("daily_official_energy_snapshot")
daily_schedule = ScheduleDefinition(job=daily_job, cron_schedule="0 6 * * *", execution_timezone="America/Edmonton")
defs = Definitions(assets=[official_public_snapshot, public_data_quality, municipality_energy_marts], jobs=[daily_job], schedules=[daily_schedule])
