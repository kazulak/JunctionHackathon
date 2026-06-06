from __future__ import annotations

from typing import Any

from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends.simulator import run_simulator_backend
from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.syndromes import extract_detection_events


def describe_pipeline(config: dict[str, Any]) -> list[str]:
    """Return a simple input -> function -> output description."""
    bases = ", ".join(_basis_list(config["code"]["basis"]))
    return [
        "config YAML -> load normal Python dict",
        f"basis list -> {bases}",
        "code + noise + basis -> build_surface_code_circuit -> "
        "(stim_circuit, detector_model, measurement_order, circuit_info)",
        "backend + circuit tuple -> run_simulator_backend -> (measurements, counts, raw_info)",
        "circuit tuple + raw tuple -> extract_detection_events -> "
        "(detection_events, observable_flips, syndrome_info)",
        "decoder + syndrome tuple -> decode_observable_rate -> "
        "(predicted_observables, logical_failures, ler, uncertainty, decoder_info)",
        "all tuples -> write artifacts and summary",
    ]


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
        circuit = build_surface_code_circuit(config["code"], config["noise"], basis)
        raw = run_simulator_backend(config["backend"], circuit)
        syndromes = extract_detection_events(circuit, raw)
        decoded = decode_observable_rate(config["decoder"], circuit, syndromes)

        _predicted, _failures, ler, uncertainty, decoder_info = decoded
        metrics = {
            "basis": basis,
            "ler": ler,
            "uncertainty": uncertainty,
            "logical_failures": decoder_info["logical_failures"],
            "shots": decoder_info["shots"],
        }

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
