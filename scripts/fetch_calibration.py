"""Download the current IQM calibration (quality metric set) for patch selection and noise.

Read-only API call with the token from `.env`; nothing is executed, no credits are used.
The file has the same observation-set format as configs/calibration/emerald_2026-06-06T*.json.

    python scripts/fetch_calibration.py --output-dir configs/calibration
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.backends.iqm_hardware import _load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("configs/calibration"))
    parser.add_argument("--quantum-computer", default=None, help="Defaults to IQM_QUANTUM_COMPUTER from .env.")
    args = parser.parse_args()

    _load_dotenv()
    from iqm.iqm_client import IQMClient

    computer = args.quantum_computer or os.environ.get("IQM_QUANTUM_COMPUTER", "emerald")
    client = IQMClient(os.environ.get("IQM_SERVER_URL", "https://resonance.meetiqm.com"), quantum_computer=computer)
    metric_set = client.get_quality_metric_set()
    data = metric_set.model_dump(mode="json")
    data["fetched_for_quantum_computer"] = computer
    data["calibration_set_id"] = str(data.get("describes_id"))

    stamp = str(data["created_timestamp"]).replace(":", "_").replace(" ", "T")[:19]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / f"{computer}_{stamp}Z.json"
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"Calibration set {data['calibration_set_id']} ({data['dut_label']}), created {data['created_timestamp']}")
    print(f"Saved {len(data['observations'])} observations to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
