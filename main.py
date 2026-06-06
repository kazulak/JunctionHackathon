from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qec_pipeline.config import config_summary, load_experiment_config
from qec_pipeline.pipeline import describe_pipeline, run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a modular QEC LER pipeline.")
    parser.add_argument(
        "config_path",
        nargs="?",
        type=Path,
        help="Path to YAML experiment config. Same as --config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
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
    config_path = args.config or args.config_path or Path("configs/demo_stim_no_noise.yaml")
    config = load_experiment_config(config_path)

    if args.print_config:
        print(f"Config file: {config_path}")
        print(config_summary(config))

    if args.dry_run:
        print("\nPipeline plan:")
        for index, stage in enumerate(describe_pipeline(config), start=1):
            print(f"{index}. {stage}")
        return 0

    try:
        run_dir, basis_results, _notes = run_pipeline(config)
    except NotImplementedError as exc:
        print(f"Pipeline stage not implemented yet: {exc}", file=sys.stderr)
        return 2

    print(f"Done: {config['experiment']['name']}")
    print(f"Artifacts: {run_dir}")
    for basis, _circuit, _raw, _syndromes, decoded, _metrics in basis_results:
        _predicted, _failures, ler, uncertainty, _decoder_info = decoded
        print(f"{basis}: LER {ler:.6g} +/- {uncertainty:.3g}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
