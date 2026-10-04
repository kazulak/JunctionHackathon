"""Re-decode a finished sweep's saved raw measurements with another decoder (no credits).

    python scripts/redecode_sweep.py results/<sweep>/<timestamp> --decoder pymatching_pij
    python scripts/redecode_sweep.py results/<sweep>/<timestamp> --decoder pymatching_calibrated
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.artifacts import utc_timestamp
from qec_pipeline.sweeps import redecode_sweep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep_dir", type=Path)
    parser.add_argument("--decoder", default="pymatching_pij")
    parser.add_argument("--folds", type=int, default=2, help="Cross-fitting folds for pymatching_pij.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    decoder = {"name": args.decoder, "options": {"folds": args.folds} if args.decoder == "pymatching_pij" else {}}
    output = args.output or args.sweep_dir.parent / f"{args.sweep_dir.name}_redecoded_{args.decoder}_{utc_timestamp()}"
    result = redecode_sweep(args.sweep_dir, decoder, output)
    print(f"Re-decoded sweep: {result}")
    print((result / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
