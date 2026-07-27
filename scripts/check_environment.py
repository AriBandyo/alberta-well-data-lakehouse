"""Validate local prerequisites and installed Python packages."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_MODULES = {
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "duckdb": "duckdb",
    "pyspark": "pyspark",
    "delta-spark": "delta",
    "dbt-duckdb": "dbt",
    "dagster": "dagster",
    "dagster-dbt": "dagster_dbt",
    "python-dotenv": "dotenv",
    "requests": "requests",
    "matplotlib": "matplotlib",
    "pytest": "pytest",
    "ruff": "ruff",
    "mypy": "mypy",
}


def check_python() -> bool:
    version = sys.version_info
    supported = (3, 10) <= (version.major, version.minor) < (3, 14)
    status = "OK" if supported else "ERROR"
    print(f"[{status}] Python {version.major}.{version.minor}.{version.micro}")
    if not supported:
        print("        Supported versions are Python 3.10 through 3.13.")
    return supported


def check_java() -> bool:
    java = shutil.which("java")
    if java is None:
        print("[ERROR] Java was not found on PATH.")
        print("        Install OpenJDK 17 before running the PySpark/Delta pipeline.")
        print("        The official snapshot pipeline can still run without Spark by using `make public-data`.")
        return False

    try:
        result = subprocess.run(
            [java, "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[ERROR] Java could not be executed: {exc}")
        return False

    output = (result.stderr or result.stdout).splitlines()
    version_line = output[0] if output else "unknown version"
    print(f"[OK] Java: {version_line}")
    return result.returncode == 0


def check_modules() -> bool:
    all_available = True
    for package, module in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module)
            print(f"[OK] {package}")
        except Exception as exc:  # Import failures may include native-library errors.
            all_available = False
            print(f"[ERROR] {package}: {exc}")
    return all_available


def check_env_file() -> bool:
    env_path = Path(".env")
    if env_path.is_file():
        print(f"[OK] Environment file: {env_path.resolve()}")
        return True
    print("[ERROR] .env was not found in the current directory.")
    return False


def main() -> int:
    print("Alberta Public Energy Lakehouse environment check")
    print("=" * 44)
    python_ok = check_python()
    env_ok = check_env_file()
    modules_ok = check_modules()
    java_ok = check_java()

    print("=" * 44)
    if python_ok and env_ok and modules_ok and java_ok:
        print("Environment is ready for the full pipeline.")
        return 0
    if python_ok and env_ok and modules_ok:
        print("Python environment is ready; Java 17 is still required for Spark.")
        return 2
    print("Environment setup is incomplete.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
