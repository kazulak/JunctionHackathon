"""Fit calibration-noise scales to IQM hardware data at r=1.

Replaces the old practice of picking the noise variant with the *lowest* simulated
LER (ERRATA E2). Only r=1 hardware data is used: from r=2 onward the hardware data
is destroyed by mid-circuit measure/reset (ERRATA E5), so it cannot calibrate a
Pauli noise model.

Two steps:

    # 1. Extract per-detector firing counts from raw hardware runs (needs results/).
    python scripts/fit_noise_to_hardware.py export-targets \\
        --config configs/sweep_d3_baseline_sim.yaml \\
        --run results/<hardware_sweep>/<ts>/runs/<..._rounds_1>/<ts> \\
        --output baselines/post_hackathon/noise_fit_targets_r1/targets.json

    # 2. Grid-search noise scales against the archived targets (no results/ needed).
    python scripts/fit_noise_to_hardware.py fit \\
        --config configs/sweep_d3_baseline_sim.yaml \\
        --targets baselines/post_hackathon/noise_fit_targets_r1/targets.json

The objective is the binomial deviance summed over every detector and the raw
logical observable, both bases. Detectors are correlated, so this is a
pseudo-likelihood: use it to rank scales, not for exact confidence intervals.
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.codes import get_code_builder
from qec_pipeline.config import load_experiment_config
from qec_pipeline.provenance import run_provenance

DEFAULT_GRID = {
    "two_qubit_scale": [0.75, 1.0, 1.5, 2.0, 3.0],
    "measurement_scale": [0.75, 1.0, 1.5, 2.0, 3.0],
    "idle_scale": [0.5, 1.0, 2.0, 4.0, 8.0],
}
BASES = ("memory_z", "memory_x")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export-targets", help="Extract r=1 hardware detector counts.")
    export.add_argument("--config", type=Path, required=True, help="Simulator config matching the hardware run.")
    export.add_argument("--run", type=Path, action="append", required=True, help="Hardware run dir (repeatable).")
    export.add_argument("--output", type=Path, required=True)

    fit = commands.add_parser("fit", help="Grid-search noise scales against archived targets.")
    fit.add_argument("--config", type=Path, required=True)
    fit.add_argument("--targets", type=Path, required=True)
    fit.add_argument("--shots", type=int, default=50000, help="Simulated shots per grid point and basis.")
    fit.add_argument("--seed", type=int, default=1)
    fit.add_argument("--output", type=Path, default=None, help="Write fit_results.json here.")
    fit.add_argument(
        "--grid",
        default=None,
        help='JSON grid overriding the default, e.g. {"idle_scale": [0, 0.25, 0.5]}.',
    )

    args = parser.parse_args()
    if args.command == "export-targets":
        targets = export_targets(load_experiment_config(args.config), args.run)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
        print(f"Targets: {args.output}")
        return 0

    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    grid = {**DEFAULT_GRID, **(json.loads(args.grid) if args.grid else {})}
    result = fit_scales(load_experiment_config(args.config), targets, grid, args.shots, args.seed)
    for row in result["ranking"][:5]:
        print(f"deviance {row['deviance']:9.2f}  {row['scales']}")
    print("Best:", result["best"]["scales"])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Fit results: {args.output}")
    return 0


def export_targets(config: dict[str, Any], run_dirs: list[Path]) -> dict[str, Any]:
    """Per-detector firing counts and raw observable flips at r=1, pooled over runs."""
    targets: dict[str, Any] = {
        "description": "IQM hardware r=1 detector firing counts used to fit simulator noise scales.",
        "exported_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": config.get("_config_path"),
        "sources": [str(path) for path in run_dirs],
        "bases": {},
    }
    for basis in BASES:
        reference = _basis_circuit(config, basis).without_noise()
        detector_counts = np.zeros(reference.num_detectors, dtype=int)
        observable_flips = 0
        shots = 0
        for run_dir in run_dirs:
            basis_dir = run_dir / basis
            circuit = stim.Circuit.from_file(basis_dir / "circuit.stim")
            if circuit.without_noise() != reference:
                raise ValueError(f"{basis_dir} was not produced by {config.get('_config_path')} at r=1")
            raw = np.load(basis_dir / "raw_measurements.npz")["measurements"].astype(bool)
            detections, observables = circuit.compile_m2d_converter().convert(
                measurements=raw,
                separate_observables=True,
            )
            detector_counts += detections.sum(axis=0)
            observable_flips += int(observables.any(axis=1).sum())
            shots += len(raw)
        targets["bases"][basis] = {
            "shots": shots,
            "detector_counts": detector_counts.tolist(),
            "observable_flip_count": observable_flips,
        }
    return targets


def fit_scales(
    config: dict[str, Any],
    targets: dict[str, Any],
    grid: dict[str, list[float]],
    shots: int,
    seed: int,
) -> dict[str, Any]:
    names = list(grid)
    ranking = []
    for values in itertools.product(*(grid[name] for name in names)):
        scales = dict(zip(names, values, strict=True))
        deviance = 0.0
        for basis, target in targets["bases"].items():
            rates = simulated_rates(config, basis, scales, shots, seed)
            observed = np.array(target["detector_counts"] + [target["observable_flip_count"]], dtype=float)
            deviance += binomial_deviance(observed, float(target["shots"]), rates)
        ranking.append({"scales": scales, "deviance": deviance})
    ranking.sort(key=lambda row: row["deviance"])
    return {
        "method": "grid search, binomial deviance over r=1 detectors + raw observable (pseudo-likelihood)",
        "provenance": run_provenance(),
        "config": config.get("_config_path"),
        "simulated_shots": shots,
        "grid": grid,
        "best": ranking[0],
        "ranking": ranking,
    }


def simulated_rates(
    config: dict[str, Any],
    basis: str,
    scales: dict[str, float],
    shots: int,
    seed: int,
) -> np.ndarray:
    """Detector firing probabilities followed by the raw observable flip probability."""
    circuit = _basis_circuit(config, basis, scales)
    sampler = circuit.compile_detector_sampler(seed=seed)
    detections, observables = sampler.sample(shots, separate_observables=True)
    return np.concatenate([detections.mean(axis=0), [observables.any(axis=1).mean()]])


def binomial_deviance(counts: np.ndarray, shots: float, probabilities: np.ndarray) -> float:
    """2 * (log L_saturated - log L_model) summed over independent binomials."""
    p = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    observed = np.clip(counts / shots, 1e-12, 1.0 - 1e-12)
    log_ratio = counts * np.log(observed / p) + (shots - counts) * np.log((1 - observed) / (1 - p))
    return float(2.0 * log_ratio.sum())


def _basis_circuit(
    config: dict[str, Any],
    basis: str,
    scales: dict[str, float] | None = None,
) -> stim.Circuit:
    run_config = copy.deepcopy(config)
    run_config["code"]["rounds"] = 1
    options = dict(run_config["noise"].get("options") or {})
    options.update(scales or {})
    run_config["noise"]["options"] = options
    circuit = get_code_builder(run_config["code"].get("family", "surface_code"))(
        run_config["code"],
        run_config["noise"],
        basis,
    )
    return prepare_circuit_for_execution(run_config, circuit)[0]


if __name__ == "__main__":
    raise SystemExit(main())
