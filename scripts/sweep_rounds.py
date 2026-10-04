from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.config import load_experiment_config
from qec_pipeline.sweeps import preflight_rounds_sweep, round_values, run_rounds_sweep


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
        "--set",
        action="append",
        default=[],
        metavar="DOTTED.KEY=VALUE",
        help=(
            "Override a config value (YAML-parsed), e.g. backend.options.dynamical_decoupling=false, "
            "backend.options.active_reset_cycles=null, code.basis=memory_z, backend.shots=1000."
        ),
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help=(
            "IQM only: build, transpile, and validate every circuit against the live backend "
            "without submitting a job (no credits)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the round values that would run.",
    )
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    for item in args.set:
        apply_override(config, item)
    rounds = round_values(args.rounds[0], args.rounds[1], args.rounds[2])

    if args.dry_run:
        print(f"Config: {args.config}")
        print(f"Rounds: {rounds}")
        print(f"Backend: {config['backend']['name']}")
        print(f"Basis: {config['code']['basis']}")
        return 0

    if args.preflight:
        if config["backend"]["name"] != "iqm_hardware":
            raise SystemExit("--preflight is only meaningful for iqm_hardware configs")
        for row in preflight_rounds_sweep(config, rounds):
            print(
                f"r={row['rounds']} {row['basis']}: reset={row['mid_circuit_reset']} "
                f"CZ={row['two_qubit_gates']} ops={row['transpiled_ops']} "
                f"active_reset_cycles={row['active_reset_cycles']} dd={row['dd_mode']}"
            )
        print(f"Physical qubits: {row['physical_qubits']}")
        print("Preflight OK: nothing was submitted.")
        return 0

    sweep_dir = run_rounds_sweep(config, rounds, output_root=args.output_root)
    print(f"Sweep artifacts: {sweep_dir}")
    print(f"CSV: {sweep_dir / 'sweep_results.csv'}")
    print(f"Plot: {sweep_dir / 'ler_vs_rounds.png'}")
    return 0


def apply_override(config: dict, item: str) -> None:
    """Set config[a][b][c] = value for an override 'a.b.c=value' (value parsed as YAML)."""
    import yaml

    if "=" not in item:
        raise SystemExit(f"--set expects DOTTED.KEY=VALUE, got {item!r}")
    key, raw_value = item.split("=", 1)
    *parents, leaf = key.split(".")
    node = config
    for part in parents:
        node = node.setdefault(part, {})
    node[leaf] = yaml.safe_load(raw_value)
    if parents[:1] == ["experiment"] or key == "experiment.name":
        return
    config["experiment"]["name"] = f"{config['experiment']['name']}__{key.split('.')[-1]}={raw_value}"


if __name__ == "__main__":
    raise SystemExit(main())
