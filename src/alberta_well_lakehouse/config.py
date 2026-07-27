from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    project_root: Path
    raw_dir: Path
    bronze_dir: Path
    silver_dir: Path
    silver_export_dir: Path
    dbt_project_dir: Path
    dbt_profiles_dir: Path
    spark_master: str
    spark_shuffle_partitions: int

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(os.getenv("PROJECT_ROOT", ".")).resolve()

        def resolve(name: str, default: str) -> Path:
            value = Path(os.getenv(name, default))
            return value if value.is_absolute() else root / value

        return cls(
            project_root=root,
            raw_dir=resolve("RAW_DIR", "data/raw"),
            bronze_dir=resolve("BRONZE_DIR", "lakehouse/bronze"),
            silver_dir=resolve("SILVER_DIR", "lakehouse/silver"),
            silver_export_dir=resolve("SILVER_EXPORT_DIR", "warehouse/silver_exports"),
            dbt_project_dir=resolve("DBT_PROJECT_DIR", "dbt/alberta_well_analytics"),
            dbt_profiles_dir=resolve("DBT_PROFILES_DIR", "dbt/alberta_well_analytics"),
            spark_master=os.getenv("SPARK_MASTER", "local[*]"),
            spark_shuffle_partitions=int(os.getenv("SPARK_SHUFFLE_PARTITIONS", "8")),
        )

    def ensure_directories(self) -> None:
        for path in (
            self.raw_dir,
            self.bronze_dir,
            self.silver_dir,
            self.silver_export_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
