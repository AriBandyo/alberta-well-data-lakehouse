from pathlib import Path


from alberta_well_lakehouse.public_data import PublicPaths, build_gold, build_silver, load_bronze, municipality_key, quality_report

ROOT = Path(__file__).resolve().parents[1]


def test_official_snapshot_values_are_present() -> None:
    paths = PublicPaths.from_root(ROOT)
    bronze = load_bronze(paths)
    oil = bronze["oil"].set_index("municipality")
    gas = bronze["gas"].set_index("municipality")
    wells = bronze["wells"].set_index("municipality")
    assert oil.loc["Bonnyville No. 87", "value"] == 32_500_000
    assert gas.loc["Rocky View County", "value"] == 1_700_000_000
    assert wells.loc["Greenview No. 16", "value"] == 571


def test_quality_checks_pass() -> None:
    paths = PublicPaths.from_root(ROOT)
    report = quality_report(load_bronze(paths))
    assert (report["status"] == "PASS").all()


def test_gold_mart_contains_expected_metrics() -> None:
    paths = PublicPaths.from_root(ROOT)
    bronze = load_bronze(paths)
    gold = build_gold(build_silver(paths, bronze))
    summary = gold["mart_municipality_energy_summary"].set_index("municipality")
    assert summary.loc["Opportunity No. 17", "oil_m3_2025"] == 3_100_000
    assert summary.loc["Opportunity No. 17", "gas_m3_2025"] == 118_600_000
    assert summary.loc["Opportunity No. 17", "well_count_2024"] == 99
    assert municipality_key("Opportunity No. 17") == municipality_key("Opportunity No. 17")
