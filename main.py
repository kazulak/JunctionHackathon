from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qec_pipeline.config import load_experiment_config
from qec_pipeline.pipeline import describe_pipeline, run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a modular QEC LER pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/demo_no_noise.yaml"),
        help="Path to YAML experiment config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load config and print planned stages without running quantum code.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print normalized config summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_experiment_config(args.config)

    if args.print_config:
        print(config.summary())

    if args.dry_run:
        print("Pipeline plan:")
        for index, stage in enumerate(describe_pipeline(config), start=1):
            print(f"{index}. {stage}")
        return 0

    try:
        state = run_pipeline(config)
    except NotImplementedError as exc:
        print(f"Pipeline stage not implemented yet: {exc}", file=sys.stderr)
        return 2

    print(f"Done: {state.config.experiment.name}")
    if state.run_dir is not None:
        print(f"Artifacts: {state.run_dir}")
    if state.decoder_result is not None:
        print(f"LER: {state.decoder_result.ler:.6g} +/- {state.decoder_result.uncertainty:.3g}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
