"""LER-vs-rounds sweeps: run, preflight, re-decode, and summarize."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from qec_pipeline.analysis.metrics import fit_per_round_error
from qec_pipeline.analysis.plots import plot_vs_rounds
from qec_pipeline.analysis.tables import SWEEP_COLUMNS, fmt, wilson_text, write_csv
from qec_pipeline.artifacts import load_basis_run, sweep_basis_dirs, utc_timestamp
from qec_pipeline.circuit_preparation import build_circuit
from qec_pipeline.codes import build_code_circuit
from qec_pipeline.decoders import get_decoder
from qec_pipeline.mapping import select_mapping_from_config
from qec_pipeline.measurements import measurement_order_from_stim_circuit
from qec_pipeline.pipeline import basis_list, build_basis_metrics, check_single_layout, run_experiments
from qec_pipeline.provenance import provenance_line, run_provenance
from qec_pipeline.stim_utils import stim_to_dense
from qec_pipeline.syndromes import extract_detection_events


def round_values(start: int, stop: int, points: int) -> list[int]:
    """Return inclusive integer round values from start to stop."""
    if start <= 0 or stop <= 0:
        raise ValueError("round values must be positive")
    if points <= 0:
        raise ValueError("points must be positive")
    if points == 1:
        return [start]

    step = (stop - start) / (points - 1)
    values = [int(round(start + index * step)) for index in range(points)]
    if len(set(values)) != len(values):
        raise ValueError("round range produced duplicate integer values; use fewer points or a wider range")
    return values


def run_rounds_sweep(base_config: dict[str, Any], rounds: list[int], output_root: Path | None = None) -> Path:
    """Run every round value (one IQM batch job on hardware) and write CSV/JSON/plots/summary.

    The qubit layout is selected once and pinned for every round value, so an
    LER-vs-rounds curve never mixes different physical patches.
    """
    base_config = pin_sweep_mapping(base_config)
    root = output_root or Path(base_config["artifacts"].get("root", "results"))
    sweep_dir = root / f"{base_config['experiment']['name']}_rounds_sweep" / utc_timestamp()
    sweep_dir.mkdir(parents=True, exist_ok=False)

    configs = [_round_config(base_config, value, runs_root=sweep_dir / "runs") for value in rounds]
    rows = []
    results = run_experiments(configs, require_single_layout=True)
    for config, (run_dir, basis_results, notes) in zip(configs, results, strict=True):
        rows += [_sweep_row(config["code"]["rounds"], result[-1], run_dir, notes) for result in basis_results]
    _write_sweep_outputs(sweep_dir, base_config, rounds, rows)
    return sweep_dir


def preflight_rounds_sweep(base_config: dict[str, Any], rounds: list[int]) -> list[dict[str, Any]]:
    """Build, transpile, and validate every circuit of an IQM sweep WITHOUT submitting it.

    Connects to IQM read-only (backend description + run-request construction); no job is
    created and no credits are used. Returns one summary row per circuit.
    """
    from qec_pipeline.backends.iqm_hardware import prepare_iqm_batch

    base_config = pin_sweep_mapping(base_config)
    labels, requests = [], []
    for value in rounds:
        config = _round_config(base_config, value)
        for basis in basis_list(config["code"]["basis"]):
            labels.append((int(value), basis))
            requests.append({"circuit": build_circuit(config, basis), "mapping": config["mapping"]})
    check_single_layout([request["circuit"] for request in requests])

    _backend, prepared, compile_options = prepare_iqm_batch(base_config["backend"], requests)
    rows = []
    for (value, basis), item in zip(labels, prepared, strict=True):
        ops = dict(item["transpiled_circuit"].count_ops())
        rows.append(
            {
                "rounds": value,
                "basis": basis,
                "mid_circuit_reset": item["mid_circuit_reset"],
                "physical_qubits": item["physical_loci"]["physical_qubits"],
                "transpiled_ops": ops,
                "two_qubit_gates": int(ops.get("cz", 0)),
                "active_reset_cycles": compile_options.active_reset_cycles,
                "dd_mode": str(compile_options.dd_mode),
            }
        )
    return rows


def redecode_sweep(sweep_dir: Path, decoder: dict[str, Any], output_dir: Path) -> Path:
    """Decode the saved raw measurements of a finished sweep with another decoder.

    Needs runs saved with `artifacts.save_raw_measurements: true`. The detector error
    model is rebuilt from each run's saved (noisy) `circuit.stim`, so hardware data can
    be re-analysed offline without spending credits.
    """
    rows = []
    for basis_dir in sweep_basis_dirs(sweep_dir):
        run = load_basis_run(basis_dir)
        stim_circuit, circuit_info = run["circuit"], run["circuit_info"]
        detector_model = stim_circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
        circuit = (stim_circuit, detector_model, measurement_order_from_stim_circuit(stim_circuit), circuit_info)
        syndromes = extract_detection_events(circuit, (run["measurements"], None, {}))
        decoded = get_decoder(decoder["name"])(decoder, circuit, syndromes)
        metrics = build_basis_metrics(basis_dir.name, int(circuit_info["rounds"]), decoded, syndromes[2])
        rows.append(_sweep_row(int(circuit_info["rounds"]), metrics, basis_dir.parent, [f"redecoded from {basis_dir}"]))

    if not rows:
        raise ValueError(f"No runs with raw measurements found under {sweep_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    rounds = sorted({row["rounds"] for row in rows})
    base_config = {"experiment": {"name": f"redecode_{decoder['name']}"}, "_config_path": str(sweep_dir)}
    _write_sweep_outputs(output_dir, base_config, rounds, rows)
    return output_dir


def pin_sweep_mapping(base_config: dict[str, Any]) -> dict[str, Any]:
    """Return a config whose mapping is a fixed Stim-to-hardware assignment.

    Configs that already pin `mapping.hardware_patch.stim_to_hardware`, or use no
    mapping, are returned unchanged.
    """
    mapping = base_config.get("mapping") or {}
    if mapping.get("strategy", "none") in {"none", None}:
        return base_config
    if (mapping.get("hardware_patch") or {}).get("stim_to_hardware"):
        return base_config

    config = copy.deepcopy(base_config)
    code = config["code"]
    stim_circuit = build_code_circuit(code, {"model": "no_noise", "parameters": {}}, basis_list(code["basis"])[0])[0]
    selected = select_mapping_from_config(config["mapping"], stim_circuit, stim_to_dense(stim_circuit))
    config["mapping"]["hardware_patch"] = {"stim_to_hardware": selected["stim_to_hardware"]}
    config["mapping"]["pinned_from_strategy"] = mapping.get("strategy")
    if selected.get("strategy") == "calibration_routed_layout" or selected.get("routed_code_edges"):
        config["mapping"]["options"] = dict(config["mapping"].get("options") or {}, allow_routing=True)
    return config


def _round_config(base_config: dict[str, Any], rounds: int, runs_root: Path | None = None) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["code"]["rounds"] = int(rounds)
    config["experiment"]["name"] = f"{base_config['experiment']['name']}_rounds_{rounds}"
    if runs_root is not None:
        config["artifacts"]["root"] = str(runs_root)
    return config


def _sweep_row(rounds: int, metrics: dict[str, Any], run_dir: Path, notes: list[str]) -> dict[str, Any]:
    return {
        "rounds": int(rounds),
        "basis": metrics["basis"],
        "ler": float(metrics["ler"]),
        "uncertainty": float(metrics["uncertainty"]),
        "ler_ci_low": metrics.get("ler_ci_low"),
        "ler_ci_high": metrics.get("ler_ci_high"),
        "logical_error_per_round": metrics.get("logical_error_per_round"),
        "logical_error_per_round_uncertainty": metrics.get("logical_error_per_round_uncertainty"),
        "logical_failures": int(metrics["logical_failures"]),
        "shots": int(metrics["shots"]),
        "mean_detector_firing_rate": metrics.get("mean_detector_firing_rate"),
        "max_detector_firing_rate": metrics.get("max_detector_firing_rate"),
        "mean_syndrome_weight": metrics.get("mean_syndrome_weight"),
        "original_shots": metrics.get("original_shots", metrics["shots"]),
        "kept_shots": metrics.get("kept_shots", metrics["shots"]),
        "postselection_fraction": metrics.get("postselection_fraction", 1.0),
        "selection_is_in_sample": bool(metrics.get("selection_is_in_sample", False)),
        "run_dir": str(run_dir),
        "notes": "; ".join(notes),
    }


def _write_sweep_outputs(sweep_dir: Path, base_config: dict[str, Any], rounds: list[int], rows: list[dict]) -> None:
    provenance = run_provenance()
    fits = {
        basis: fit_per_round_error([row for row in rows if row["basis"] == basis])
        for basis in sorted({row["basis"] for row in rows})
    }
    write_csv(sweep_dir / "sweep_results.csv", rows, fieldnames=SWEEP_COLUMNS)
    payload = {
        "base_experiment": base_config["experiment"]["name"],
        "config_path": base_config.get("_config_path"),
        "provenance": provenance,
        "rounds": rounds,
        "rows": rows,
        "per_round_fits": fits,
    }
    (sweep_dir / "sweep_results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if not rows:
        raise ValueError("cannot plot an empty sweep")
    plot_vs_rounds(
        rows, sweep_dir / "ler_vs_rounds.png", "ler", "Logical error rate", "LER vs rounds", yerr_key="uncertainty"
    )
    plot_vs_rounds(
        rows,
        sweep_dir / "detector_rate_vs_rounds.png",
        "mean_detector_firing_rate",
        "Mean detector firing rate",
        "Detector rate vs rounds",
    )

    lines = [
        f"# Rounds Sweep: {base_config['experiment']['name']}",
        "",
        provenance_line(provenance),
        f"- Config: `{base_config.get('_config_path', 'unknown')}`",
        f"- Rounds: {rounds}",
        "- Results: `sweep_results.csv`, `sweep_results.json`",
        "- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`",
        "",
        "## Results",
        "",
        "LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.",
        "",
        "| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original "
        "| Failures | Shots | Selection |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        selection = "in-sample (optimistic)" if row.get("selection_is_in_sample") else "fixed / out-of-sample"
        lines.append(
            f"| {row['rounds']} | {row['basis']} | {fmt(row['ler'])} | "
            f"{wilson_text(row['logical_failures'], row['shots'])} | {fmt(row.get('logical_error_per_round'))} | "
            f"{fmt(row.get('mean_detector_firing_rate'))} | {row['kept_shots']}/{row['original_shots']} | "
            f"{row['logical_failures']} | {row['shots']} | {selection} |"
        )
    lines += [
        "",
        "## Per-round fit",
        "",
        "Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.",
        "",
        "| Basis | Fit points | Error per round | 1-sigma | Amplitude A |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for basis, fit in fits.items():
        lines.append(
            f"| {basis} | {fit['fit_points']} | {fmt(fit['fitted_logical_error_per_round'])} | "
            f"{fmt(fit['fitted_logical_error_per_round_uncertainty'])} | {fmt(fit['fit_amplitude'])} |"
        )
    (sweep_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
