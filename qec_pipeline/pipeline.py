from __future__ import annotations

from typing import Any

from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends import get_backend_runner
from qec_pipeline.backends.iqm_hardware import run_iqm_hardware_batch_backend
from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.codes import get_code_builder
from qec_pipeline.decoders import get_decoder
from qec_pipeline.syndromes import extract_detection_events


def describe_pipeline(config: dict[str, Any]) -> list[str]:
    """Return a simple input -> function -> output description."""
    bases = ", ".join(_basis_list(config["code"]["basis"]))
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
        stages.append(
            "selected mapping + IQM calibration file -> inject per-qubit/per-coupler Stim noise"
        )
    if (
        config.get("backend", {}).get("name") == "iqm_hardware"
        and bool(config.get("backend", {}).get("options", {}).get("batch_submit", True))
    ):
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
    """Run the configured experiment.

    For `code.basis: both`, this runs memory-Z and memory-X in the same job.

    Return tuple:
        (run_dir, basis_results, notes)
    """
    run_dir = prepare_run_directory(config)
    notes = []
    basis_results: list[tuple] = []
    prepared_basis = []

    for basis in _basis_list(config["code"]["basis"]):
        circuit = _build_circuit(config["code"], config["noise"], basis)
        circuit = prepare_circuit_for_execution(config, circuit)
        prepared_basis.append((basis, circuit))

    if _use_iqm_batch_submit(config["backend"], len(prepared_basis)):
        raws = run_iqm_hardware_batch_backend(
            config["backend"],
            [
                {"circuit": circuit, "mapping": config["mapping"]}
                for _basis, circuit in prepared_basis
            ],
        )
    else:
        raws = [
            _run_backend(config["backend"], config["mapping"], circuit)
            for _basis, circuit in prepared_basis
        ]

    for (basis, circuit), raw in zip(prepared_basis, raws):
        syndromes = extract_detection_events(circuit, raw)
        _detection_events, _observable_flips, syndrome_info = syndromes
        decoded = _run_decoder(config["decoder"], circuit, syndromes)

        _predicted, _failures, ler, uncertainty, decoder_info = decoded
        metrics = {
            "basis": basis,
            "ler": ler,
            "uncertainty": uncertainty,
            "logical_failures": decoder_info["logical_failures"],
            "shots": decoder_info["shots"],
            "mean_detector_firing_rate": syndrome_info["mean_detector_firing_rate"],
            "max_detector_firing_rate": syndrome_info["max_detector_firing_rate"],
            "mean_syndrome_weight": syndrome_info["mean_syndrome_weight"],
            "decoder_info": decoder_info,
        }
        if "original_shots" in decoder_info:
            metrics["original_shots"] = decoder_info["original_shots"]
            metrics["kept_shots"] = decoder_info.get("kept_shots", decoder_info["shots"])
            metrics["postselection_fraction"] = decoder_info.get("postselection_fraction", 1.0)
        rounds = int(config["code"].get("rounds", 1))
        if rounds > 1:
            per_round_ler, per_round_uncertainty = _per_round_ler(ler, uncertainty, rounds)
            metrics["rounds"] = rounds
            metrics["logical_error_per_round"] = per_round_ler
            metrics["logical_error_per_round_uncertainty"] = per_round_uncertainty
        if "noise_sweep" in decoder_info:
            metrics["decoder_noise_sweep"] = decoder_info["noise_sweep"]

        basis_run_dir = run_dir / basis
        basis_run_dir.mkdir(parents=True, exist_ok=False)
        write_run_artifacts(basis_run_dir, circuit, raw, syndromes, metrics, config["artifacts"])

        basis_results.append((basis, circuit, raw, syndromes, decoded, metrics))
        notes.append(f"{basis}: LER {ler} +/- {uncertainty}")

    write_run_summary(run_dir, config, basis_results, notes)
    return run_dir, basis_results, notes


def _basis_list(config_basis: str) -> list[str]:
    if config_basis == "both":
        return ["memory_z", "memory_x"]
    if config_basis in {"memory_z", "memory_x"}:
        return [config_basis]
    raise ValueError("code.basis must be memory_z, memory_x, or both")


def _run_backend(backend: dict[str, Any], mapping: dict[str, Any], circuit: tuple) -> tuple:
    return get_backend_runner(backend["name"])(backend, circuit, mapping)


def _build_circuit(code: dict[str, Any], noise: dict[str, Any], basis: str) -> tuple:
    return get_code_builder(code.get("family", "surface_code"))(code, noise, basis)


def _run_decoder(decoder: dict[str, Any], circuit: tuple, syndromes: tuple) -> tuple:
    return get_decoder(decoder["name"])(decoder, circuit, syndromes)


def _use_iqm_batch_submit(backend: dict[str, Any], num_circuits: int) -> bool:
    if backend.get("name") != "iqm_hardware":
        return False
    if num_circuits <= 1:
        return False
    return bool(backend.get("options", {}).get("batch_submit", True))


def _per_round_ler(total_ler: float, total_uncertainty: float, rounds: int) -> tuple[float, float]:
    """Convert total memory-failure probability to per-round probability."""
    if rounds <= 1:
        return total_ler, total_uncertainty
    clamped = min(max(float(total_ler), 0.0), 0.499999999)
    survival = 1.0 - 2.0 * clamped
    per_round = (1.0 - survival ** (1.0 / rounds)) / 2.0
    derivative = (1.0 / rounds) * survival ** ((1.0 / rounds) - 1.0)
    return float(per_round), float(abs(derivative) * total_uncertainty)
