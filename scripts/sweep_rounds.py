from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.config import load_experiment_config
from qec_pipeline.sweeps import round_values, run_rounds_sweep


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a rounds sweep and plot LER.")
    parser.add_argument("config", type=Path, help="Base YAML config.")
    parser.add_argument(
        "--rounds",
        nargs=3,
        metavar=("START", "STOP", "POINTS"),
        type=int,
        required=True,
        help="Inclusive rounds range, for example: --rounds 3 15 6",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Optional output root. Defaults to artifacts.root from YAML.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the round values that would run.",
    )
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    rounds = round_values(args.rounds[0], args.rounds[1], args.rounds[2])

    if args.dry_run:
        print(f"Config: {args.config}")
        print(f"Rounds: {rounds}")
        print(f"Backend: {config['backend']['name']}")
        print(f"Basis: {config['code']['basis']}")
        return 0

    sweep_dir = run_rounds_sweep(config, rounds, output_root=args.output_root)
    print(f"Sweep artifacts: {sweep_dir}")
    print(f"CSV: {sweep_dir / 'sweep_results.csv'}")
    print(f"Plot: {sweep_dir / 'ler_vs_rounds.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
