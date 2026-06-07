from __future__ import annotations

from typing import Any

from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends import get_backend_runner
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

    for basis in _basis_list(config["code"]["basis"]):
        circuit = _build_circuit(config["code"], config["noise"], basis)
        circuit = prepare_circuit_for_execution(config, circuit)
        raw = _run_backend(config["backend"], config["mapping"], circuit)
        syndromes = extract_detection_events(circuit, raw)
        decoded = _run_decoder(config["decoder"], circuit, syndromes)

        _predicted, _failures, ler, uncertainty, decoder_info = decoded
        metrics = {
            "basis": basis,
            "ler": ler,
            "uncertainty": uncertainty,
            "logical_failures": decoder_info["logical_failures"],
            "shots": decoder_info["shots"],
        }
        if "noise_sweep" in decoder_info:
            metrics["decoder_noise_sweep"] = decoder_info["noise_sweep"]

        basis_run_dir = run_dir / basis
        basis_run_dir.mkdir(parents=True, exist_ok=False)
        write_run_artifacts(basis_run_dir, circuit, raw, syndromes, metrics)

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
