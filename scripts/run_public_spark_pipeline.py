from pathlib import Path
import json

from alberta_well_lakehouse.public_spark import run

ROOT = Path(__file__).resolve().parents[1]
print(json.dumps(run(ROOT), indent=2))
