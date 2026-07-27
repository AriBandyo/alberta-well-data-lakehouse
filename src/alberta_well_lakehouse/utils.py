from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^A-Z0-9]", "", value.strip().upper())
    return cleaned or None


def discover_csv_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*.csv") if path.is_file())


def require_files(paths: Iterable[Path], label: str) -> list[Path]:
    result = list(paths)
    if not result:
        raise FileNotFoundError(f"No {label} CSV files were found")
    return result
