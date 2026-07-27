from __future__ import annotations

import argparse
import json
from pathlib import Path

from .public_data import run_public_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Alberta public energy data pipeline")
    parser.add_argument(
        "stage",
        nargs="?",
        default="public",
        choices=["public"],
        help="Build the official public-data snapshot pipeline",
    )
    args = parser.parse_args()
    if args.stage == "public":
        print(json.dumps(run_public_pipeline(Path.cwd()), indent=2, default=str))


if __name__ == "__main__":
    main()
