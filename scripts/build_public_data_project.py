from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from alberta_well_lakehouse.public_data import PublicPaths, run_public_pipeline

ROOT = Path(__file__).resolve().parents[1]


def format_volume(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def create_charts(paths: PublicPaths) -> None:
    summary = pd.read_csv(paths.gold / "mart_municipality_energy_summary.csv")
    chart_dir = paths.results / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    for metric, label, filename in [
        ("oil_m3_2025", "Oil production (m³)", "top_oil_production.png"),
        ("gas_m3_2025", "Natural gas production (m³)", "top_gas_production.png"),
        ("well_count_2024", "Well count", "top_well_count.png"),
    ]:
        top = summary.nlargest(8, metric).sort_values(metric)
        plt.figure(figsize=(10, 5.5))
        plt.barh(top["municipality"], top[metric])
        plt.xlabel(label)
        plt.title(f"Top municipalities by {label.lower()}")
        plt.tight_layout()
        plt.savefig(chart_dir / filename, dpi=150)
        plt.close()

    comparable = summary.dropna(subset=["combined_yoy_pct"]).sort_values("combined_yoy_pct")
    plt.figure(figsize=(10, 6))
    plt.barh(comparable["municipality"], comparable["combined_yoy_pct"])
    plt.axvline(0, linewidth=1)
    plt.xlabel("Average oil and gas year-over-year change (%)")
    plt.title("Municipality production momentum")
    plt.tight_layout()
    plt.savefig(chart_dir / "production_momentum.png", dpi=150)
    plt.close()


def create_analysis(paths: PublicPaths, metrics: dict[str, object]) -> None:
    summary = pd.read_csv(paths.gold / "mart_municipality_energy_summary.csv")
    top_oil = summary.nlargest(3, "oil_m3_2025")
    top_gas = summary.nlargest(3, "gas_m3_2025")
    growing = summary.dropna(subset=["combined_yoy_pct"]).nlargest(3, "combined_yoy_pct")
    declining = summary.dropna(subset=["combined_yoy_pct"]).nsmallest(3, "combined_yoy_pct")

    def rows(frame: pd.DataFrame, value_col: str, suffix: str = "") -> str:
        return "\n".join(
            f"- {row.municipality}: {format_volume(float(getattr(row, value_col)))}{suffix}"
            for row in frame.itertuples()
        )

    text = f"""# Actual output and findings

The pipeline processed {metrics['source_records']} official public-data records covering {metrics['municipalities']} distinct Alberta municipalities. All {metrics['quality_checks']} automated data-quality checks passed with {metrics['quality_failures']} failures.

## Snapshot totals

- Oil production represented in the included 2025 snapshot: {format_volume(float(metrics['snapshot_oil_m3']))} m³
- Natural gas production represented in the included 2025 snapshot: {format_volume(float(metrics['snapshot_gas_m3']))} m³
- Wells represented in the included 2024 well-count snapshot: {int(metrics['snapshot_reported_wells']):,}

These are totals for the curated municipalities included in this repository, not province-wide totals.

## Leading municipalities

### Oil production
{rows(top_oil, 'oil_m3_2025', ' m³')}

### Natural gas production
{rows(top_gas, 'gas_m3_2025', ' m³')}

## Production momentum

The momentum measure averages the available oil and natural-gas year-over-year changes. It is used only when at least one production measure is available.

### Strongest growth
{rows(growing, 'combined_yoy_pct', '%')}

### Largest declines
{rows(declining, 'combined_yoy_pct', '%')}

## Generated assets

- Bronze and silver CSV tables with ingestion metadata and standardized municipality keys
- Gold dimension, fact, and municipality summary tables in CSV and Parquet when PyArrow is installed
- A queryable SQLite analytics database at `warehouse/alberta_energy_analytics.sqlite`
- Tableau-ready CSV extracts and a local browser dashboard
- Ranked result tables, quality results, charts, and this analysis

## Interpretation limits

Oil and gas values use 2025 data, while well counts use 2024 data. Per-well ratios are therefore indicative comparisons, not engineering productivity measures. Prior-year and five-year baseline columns are mathematically derived from the published percentage changes and are clearly named as estimates.
"""
    (paths.results / "ANALYSIS.md").write_text(textwrap_dedent(text), encoding="utf-8")


def textwrap_dedent(value: str) -> str:
    lines = value.splitlines()
    return "\n".join(line[4:] if line.startswith("    ") else line for line in lines).strip() + "\n"


def create_dashboard(paths: PublicPaths, metrics: dict[str, object]) -> None:
    summary = pd.read_csv(paths.gold / "mart_municipality_energy_summary.csv")
    top_oil = summary.nlargest(8, "oil_m3_2025")
    top_gas = summary.nlargest(8, "gas_m3_2025")
    displayed = summary.head(20)

    def bar_rows(frame: pd.DataFrame, value_column: str) -> str:
        maximum = max(float(frame[value_column].max()), 1.0)
        rows = []
        for row in frame.itertuples():
            value = float(getattr(row, value_column))
            width = max(1.0, 100.0 * value / maximum)
            rows.append(
                f'<div class="bar-row"><span class="bar-label">{row.municipality}</span>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div>'
                f'<span class="bar-value">{format_volume(value)}</span></div>'
            )
        return "".join(rows)

    table_rows = "".join(
        "<tr>"
        f"<td>{row.municipality}</td>"
        f"<td>{float(row.oil_m3_2025):,.0f}</td>"
        f"<td>{float(row.gas_m3_2025):,.0f}</td>"
        f"<td>{float(row.well_count_2024):,.0f}</td>"
        f"<td>{float(row.combined_yoy_pct):.2f}</td>"
        f"<td>{float(row.energy_activity_score):.2f}</td>"
        "</tr>"
        for row in displayed.itertuples()
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alberta Energy Activity Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f4f6f8; color: #17212b; }}
    header {{ background: #182b3a; color: white; padding: 28px 7%; }}
    main {{ width: 86%; margin: 24px auto 48px; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 16px; }}
    .card, .panel {{ background: white; border-radius: 8px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .value {{ font-size: 26px; font-weight: 700; margin-top: 8px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }}
    .bar-row {{ display: grid; grid-template-columns: 180px 1fr 70px; gap: 10px; align-items: center; margin: 10px 0; font-size: 13px; }}
    .bar-track {{ background: #e6ebef; height: 16px; border-radius: 4px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: #294c60; }}
    .bar-value {{ text-align: right; font-variant-numeric: tabular-nums; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e4e8ec; padding: 9px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .note {{ font-size: 13px; color: #52616b; margin-top: 20px; }}
    @media (max-width: 900px) {{
      .cards, .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 130px 1fr 60px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Alberta Well and Production Analytics</h1>
    <p>Official public-data snapshot processed through bronze, silver, and gold layers</p>
  </header>
  <main>
    <section class="cards">
      <div class="card">Source records<div class="value">{metrics['source_records']}</div></div>
      <div class="card">Municipalities<div class="value">{metrics['municipalities']}</div></div>
      <div class="card">Oil in snapshot<div class="value">{format_volume(float(metrics['snapshot_oil_m3']))} m³</div></div>
      <div class="card">Gas in snapshot<div class="value">{format_volume(float(metrics['snapshot_gas_m3']))} m³</div></div>
    </section>
    <section class="grid">
      <div class="panel"><h2>Top oil production</h2>{bar_rows(top_oil, 'oil_m3_2025')}</div>
      <div class="panel"><h2>Top natural gas production</h2>{bar_rows(top_gas, 'gas_m3_2025')}</div>
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Municipality summary</h2>
      <div style="overflow:auto">
        <table>
          <thead><tr><th>Municipality</th><th>Oil m³</th><th>Gas m³</th><th>Wells</th><th>YoY %</th><th>Score</th></tr></thead>
          <tbody>{table_rows}</tbody>
        </table>
      </div>
    </section>
    <p class="note">Oil and gas values refer to 2025. Well counts refer to 2024. Snapshot totals cover only the municipalities included in the repository.</p>
  </main>
</body>
</html>"""
    (ROOT / "tableau" / "dashboard_preview.html").write_text(html, encoding="utf-8")

def main() -> None:
    metrics = run_public_pipeline(ROOT)
    paths = PublicPaths.from_root(ROOT)
    create_charts(paths)
    create_analysis(paths, metrics)
    create_dashboard(paths, metrics)
    print(json.dumps(metrics, indent=2))
    print("Generated official-snapshot lakehouse outputs, results, charts, database, and dashboard.")


if __name__ == "__main__":
    main()
