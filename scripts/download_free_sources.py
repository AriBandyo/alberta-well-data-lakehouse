from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

REGIONAL_FILES = {
    "regional-oil": os.getenv("REGIONAL_OIL_CSV_URL", "https://regionaldashboard.alberta.ca/export/opendata/Oil%20Production/csvs"),
    "regional-gas": os.getenv("REGIONAL_GAS_CSV_URL", "https://regionaldashboard.alberta.ca/export/opendata/Natural%20Gas%20Production/csvs"),
    "regional-wells": os.getenv("REGIONAL_WELL_COUNT_CSV_URL", "https://regionaldashboard.alberta.ca/export/opendata/Well%20Count/csvs"),
    "aer-st37": os.getenv("AER_ST37_EXCEL_URL", "https://static.aer.ca/prd/documents/sts/st37/ST_37_Excel.zip"),
}

PETRINEX_INFRA = {
    "petrinex-well-infrastructure": "Well%20Infrastructure",
    "petrinex-well-licence": "Well%20Licence",
    "petrinex-facility-infrastructure": "Facility%20Infrastructure",
    "petrinex-facility-operator-history": "Facility%20Operator%20History",
    "petrinex-well-facility-link": "Well%20to%20Facility%20Link",
}


def download(url: str, destination: Path, attempts: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": os.getenv("HTTP_USER_AGENT", "alberta-well-data-lakehouse/1.1")}
    timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
    error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
                response.raise_for_status()
                temporary = destination.with_suffix(destination.suffix + ".part")
                with temporary.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                temporary.replace(destination)
            print(f"Downloaded {destination} ({destination.stat().st_size:,} bytes)")
            return
        except (requests.RequestException, OSError) as exc:
            error = exc
            if attempt < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to download {url}: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download free official Alberta energy datasets")
    parser.add_argument("source", choices=[*REGIONAL_FILES, *PETRINEX_INFRA, "petrinex-volumetric", "aer-well-feature-sample"])
    parser.add_argument("--month", help="Petrinex volumetric production month in YYYY-MM format")
    parser.add_argument("--limit", type=int, default=2000, help="Maximum ArcGIS well features to download")
    args = parser.parse_args()
    out = ROOT / "data" / "external"

    if args.source == "aer-well-feature-sample":
        base_url = os.getenv(
            "AER_WELL_FEATURE_QUERY_URL",
            "https://services2.arcgis.com/jQV6VMr2Loovu7GU/ArcGIS/rest/services/AB_Well_Licence_WebM/FeatureServer/0/query",
        )
        params = {
            "where": "1=1",
            "outFields": "OBJECTID,Well_Type,Well_Category,Surface_Location,Well_Symbol,Feature_Layer_Source",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultRecordCount": str(max(1, min(args.limit, 2000))),
            "orderByFields": "OBJECTID",
            "f": "geojson",
        }
        headers = {"User-Agent": os.getenv("HTTP_USER_AGENT", "alberta-well-data-lakehouse/1.1")}
        timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
        response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        destination = out / "aer-well-feature-sample.geojson"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        print(f"Downloaded {destination} ({destination.stat().st_size:,} bytes)")
        return

    if args.source in REGIONAL_FILES:
        suffix = ".zip" if args.source == "aer-st37" else ".csv"
        download(REGIONAL_FILES[args.source], out / f"{args.source}{suffix}")
        return

    if args.source in PETRINEX_INFRA:
        filename = PETRINEX_INFRA[args.source]
        template = os.getenv(
            "PETRINEX_INFRA_API_TEMPLATE",
            "https://www.petrinex.gov.ab.ca/publicdata/API/Files/{jurisdiction}/Infra/{filename}/{format}",
        )
        url = template.format(jurisdiction="AB", filename=filename, format="CSV")
        download(url, out / f"{args.source}.csv")
        return

    if not args.month:
        parser.error("--month YYYY-MM is required for petrinex-volumetric")
    template = os.getenv(
        "PETRINEX_VOLUMETRIC_API_TEMPLATE",
        "https://www.petrinex.gov.ab.ca/publicdata/API/Files/{jurisdiction}/Vol/{month}/{format}",
    )
    url = template.format(jurisdiction="AB", month=quote(args.month), format="CSV")
    download(url, out / f"petrinex-conventional-volumetric-{args.month}.csv")


if __name__ == "__main__":
    main()
