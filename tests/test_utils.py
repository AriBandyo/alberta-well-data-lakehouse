from pathlib import Path

from alberta_well_lakehouse.utils import discover_csv_files, normalize_identifier


def test_normalize_identifier() -> None:
    assert normalize_identifier(" 100/01-02 ") == "1000102"
    assert normalize_identifier("") is None
    assert normalize_identifier(None) is None


def test_discover_csv_files(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "b.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "nested" / "a.csv").write_text("x\n2\n", encoding="utf-8")
    assert [path.name for path in discover_csv_files(tmp_path)] == ["b.csv", "a.csv"]
