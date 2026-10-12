"""Run experiments: build circuits, execute them, decode, and write artifacts.

A single run and every round of a sweep go through `run_experiments`, so all of them
share one code path; on IQM all their circuits are submitted as one batch job.
"""

from __future__ import annotations

from typing import Any

from qec_pipeline.analysis.metrics import is_postselected, per_round_ler, wilson_interval
from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends import get_backend_runner
from qec_pipeline.backends.iqm_hardware import run_iqm_hardware_batch_backend
from qec_pipeline.circuit_preparation import build_circuit
from qec_pipeline.decoders import get_decoder
from qec_pipeline.syndromes import extract_detection_events


def describe_pipeline(config: dict[str, Any]) -> list[str]:
    """Return a simple input -> function -> output description."""
    bases = ", ".join(basis_list(config["code"]["basis"]))
    stages = [
        "config YAML -> load normal Python dict",
        f"basis list -> {bases}",
        f"code family `{config['code'].get('family', 'surface_code')}` + noise + basis -> selected code builder -> "
        "(stim_circuit, detector_model, measurement_order, circuit_info)",
    ]
    mapping_strategy = config["mapping"].get("strategy")
    if mapping_strategy == "calibration_best_patch":
        stages.append("mapping calibration file + circuit -> select native patch -> initial_layout")
    if mapping_strategy == "calibration_routed_layout":
        stages.append("mapping calibration file + circuit -> select routed layout -> initial_layout")
    if config.get("noise", {}).get("model") == "iqm_calibration":
        stages.append("selected mapping + IQM calibration file -> inject per-qubit/per-coupler Stim noise")
    if _iqm_batch(config.get("backend", {})):
        stages.append("IQM backend -> submit selected circuits as one batch job before waiting")
    stages.extend(
        [
            "backend + circuit tuple -> run selected backend -> (measurements, counts, raw_info)",
            "circuit tuple + raw tuple -> extract_detection_events -> "
            "(detection_events, observable_flips, syndrome_info)",
            "decoder + syndrome tuple -> run selected decoder -> "
            "(predicted_observables, logical_failures, ler, uncertainty, decoder_info)",
            "all tuples -> write artifacts and summary",
        ]
    )
    return stages


def run_pipeline(config: dict[str, Any]) -> tuple[Any, list[tuple], list[str]]:
    """Run one experiment (`code.basis: both` runs memory-Z and memory-X).

    Returns (run_dir, basis_results, notes); each basis result is
    (basis, circuit, raw, syndromes, decoded, metrics).
    """
    return run_experiments([config])[0]


def run_experiments(configs: list[dict[str, Any]], require_single_layout: bool = False) -> list[tuple]:
    """Run several experiments that share one backend; returns (run_dir, basis_results, notes) per config.

    Every circuit is built (and, with `require_single_layout`, checked to use one qubit layout)
    before anything executes, so a hardware batch fails before spending credits.
    """
    runs = [(prepare_run_directory(config), [], []) for config in configs]  # (run_dir, basis_results, notes)
    jobs = [
        (index, basis, build_circuit(config, basis))
        for index, config in enumerate(configs)
        for basis in basis_list(config["code"]["basis"])
    ]
    if require_single_layout:
        check_single_layout([circuit for _index, _basis, circuit in jobs])

    requests = [{"circuit": circuit, "mapping": configs[index]["mapping"]} for index, _basis, circuit in jobs]
    raws = execute_circuits(configs[0]["backend"], requests)

    for (index, basis, circuit), raw in zip(jobs, raws, strict=True):
        config = configs[index]
        run_dir, basis_results, notes = runs[index]
        syndromes = extract_detection_events(circuit, raw)
        decoded = get_decoder(config["decoder"]["name"])(config["decoder"], circuit, syndromes)
        _predicted, _failures, ler, uncertainty, _info = decoded
        metrics = build_basis_metrics(basis, int(config["code"].get("rounds", 1)), decoded, syndromes[2])

        (run_dir / basis).mkdir(parents=True, exist_ok=False)
        write_run_artifacts(run_dir / basis, circuit, raw, syndromes, metrics, config["artifacts"])
        basis_results.append((basis, circuit, raw, syndromes, decoded, metrics))
        notes.append(f"{basis}: LER {ler} +/- {uncertainty}")

    for config, (run_dir, basis_results, notes) in zip(configs, runs, strict=True):
        write_run_summary(run_dir, config, basis_results, notes)
    return runs


def execute_circuits(backend: dict[str, Any], requests: list[dict[str, Any]]) -> list[tuple]:
    """Run each {"circuit", "mapping"} request; on IQM with `batch_submit` (default) as one job."""
    if _iqm_batch(backend):
        return run_iqm_hardware_batch_backend(backend, requests)
    runner = get_backend_runner(backend["name"])
    return [runner(backend, request["circuit"], request["mapping"]) for request in requests]


def check_single_layout(circuits: list[tuple]) -> None:
    """Refuse a set of circuits mapped to different physical qubit layouts."""
    layouts = set()
    for circuit in circuits:
        stim_to_hardware = (circuit[3].get("mapping") or {}).get("stim_to_hardware")
        if stim_to_hardware:
            layouts.add(tuple(sorted(stim_to_hardware.items())))
    if len(layouts) > 1:
        raise RuntimeError(f"Sweep used {len(layouts)} different qubit layouts; expected one.")


def basis_list(config_basis: str) -> list[str]:
    if config_basis == "both":
        return ["memory_z", "memory_x"]
    if config_basis in {"memory_z", "memory_x"}:
        return [config_basis]
    raise ValueError("code.basis must be memory_z, memory_x, or both")


def _iqm_batch(backend: dict[str, Any]) -> bool:
    return backend.get("name") == "iqm_hardware" and bool(backend.get("options", {}).get("batch_submit", True))


def build_basis_metrics(
    basis: str,
    rounds: int,
    decoded: tuple,
    syndrome_info: dict[str, Any],
) -> dict[str, Any]:
    """Build the metrics dictionary for one decoded basis run."""
    _predicted, _failures, ler, uncertainty, decoder_info = decoded
    failures = int(decoder_info["logical_failures"])
    shots = int(decoder_info["shots"])
    ci_low, ci_high = wilson_interval(failures, shots) if shots else (None, None)
    metrics = {
        "basis": basis,
        "rounds": int(rounds),
        "ler": ler,
        "uncertainty": uncertainty,
        "ler_ci_low": ci_low,
        "ler_ci_high": ci_high,
        "logical_failures": failures,
        "shots": shots,
        "mean_detector_firing_rate": syndrome_info["mean_detector_firing_rate"],
        "max_detector_firing_rate": syndrome_info["max_detector_firing_rate"],
        "mean_syndrome_weight": syndrome_info["mean_syndrome_weight"],
        "selection_is_in_sample": bool(decoder_info.get("selection_is_in_sample", False)),
        "decoder_info": decoder_info,
    }
    if "original_shots" in decoder_info:
        metrics["original_shots"] = decoder_info["original_shots"]
        metrics["kept_shots"] = decoder_info.get("kept_shots", decoder_info["shots"])
        metrics["postselection_fraction"] = decoder_info.get("postselection_fraction", 1.0)

    if is_postselected(metrics):
        # Postselection changes the kept fraction with r, so a per-round conversion is not meaningful.
        metrics["logical_error_per_round"] = None
        metrics["logical_error_per_round_uncertainty"] = None
    else:
        per_round, per_round_uncertainty = per_round_ler(ler, uncertainty, int(rounds))
        metrics["logical_error_per_round"] = per_round
        metrics["logical_error_per_round_uncertainty"] = per_round_uncertainty
    if "noise_sweep" in decoder_info:
        metrics["decoder_noise_sweep"] = decoder_info["noise_sweep"]
    return metrics
