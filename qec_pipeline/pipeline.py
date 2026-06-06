from __future__ import annotations

from typing import Any

from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends.iqm_hardware import run_iqm_hardware_backend
from qec_pipeline.backends.simulator import run_simulator_backend
from qec_pipeline.codes.color_code import build_color_code_circuit
from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.decoders.pymatching_decoder import decode_with_pymatching
from qec_pipeline.syndromes import extract_detection_events


def describe_pipeline(config: dict[str, Any]) -> list[str]:
    """Return a simple input -> function -> output description."""
    bases = ", ".join(_basis_list(config["code"]["basis"]))
    return [
        "config YAML -> load normal Python dict",
        f"basis list -> {bases}",
        "code + noise + basis -> build_surface_code_circuit -> "
        "(stim_circuit, detector_model, measurement_order, circuit_info)",
        "backend + circuit tuple -> run selected backend -> (measurements, counts, raw_info)",
        "circuit tuple + raw tuple -> extract_detection_events -> "
        "(detection_events, observable_flips, syndrome_info)",
        "decoder + syndrome tuple -> run selected decoder -> "
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
        circuit = _build_circuit(config["code"], config["noise"], basis)
        raw = _run_backend(config["backend"], circuit)
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


def _run_backend(backend: dict[str, Any], circuit: tuple) -> tuple:
    if backend["name"] == "simulator":
        return run_simulator_backend(backend, circuit)
    if backend["name"] == "iqm_hardware":
        return run_iqm_hardware_backend(backend, circuit)
    raise ValueError(f"Unknown backend: {backend['name']}")


def _build_circuit(code: dict[str, Any], noise: dict[str, Any], basis: str) -> tuple:
    if code["family"] == "surface_code":
        return build_surface_code_circuit(code, noise, basis)
    if code["family"] == "color_code":
        return build_color_code_circuit(code, noise, basis)
    raise ValueError(f"Unknown code family: {code['family']}")


def _run_decoder(decoder: dict[str, Any], circuit: tuple, syndromes: tuple) -> tuple:
    if decoder["name"] == "observable_rate":
        return decode_observable_rate(decoder, circuit, syndromes)
    if decoder["name"] == "pymatching":
        return decode_with_pymatching(decoder, circuit, syndromes)
    raise ValueError(f"Unknown decoder: {decoder['name']}")
