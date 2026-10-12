"""Re-decode a finished sweep's saved raw measurements with another decoder (no credits).

python scripts/redecode_sweep.py results/<sweep>/<timestamp> --decoder pymatching_pij
python scripts/redecode_sweep.py results/<sweep>/<timestamp> --decoder pymatching --option enable_correlations=true
python scripts/redecode_sweep.py results/<sweep>/<timestamp> --decoder-from configs/sweep_d3_decoder_kfold_sim.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.artifacts import utc_timestamp
from qec_pipeline.config import apply_overrides, load_experiment_config
from qec_pipeline.sweeps import redecode_sweep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep_dir", type=Path)
    parser.add_argument("--decoder", default="pymatching_pij", help="Decoder name (ignored with --decoder-from).")
    parser.add_argument("--decoder-from", type=Path, default=None, help="Use the decoder section of this config.")
    parser.add_argument(
        "--option", action="append", default=[], metavar="KEY=VALUE", help="Decoder option (YAML-parsed), repeatable."
    )
    parser.add_argument("--folds", type=int, default=None, help="Shortcut for --option folds=N (pymatching_pij).")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.decoder_from:
        decoder = load_experiment_config(args.decoder_from)["decoder"]
    else:
        decoder = {"name": args.decoder, "options": {}}
    if args.folds is not None:
        args.option.append(f"folds={args.folds}")
    decoder["options"] = decoder.get("options") or {}
    apply_overrides(decoder["options"], args.option, rename=False)

    output = (
        args.output or args.sweep_dir.parent / f"{args.sweep_dir.name}_redecoded_{decoder['name']}_{utc_timestamp()}"
    )
    result = redecode_sweep(args.sweep_dir, decoder, output)
    print(f"Re-decoded with {decoder['name']} {yaml.safe_dump(decoder['options'], default_flow_style=True).strip()}")
    print((result / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
