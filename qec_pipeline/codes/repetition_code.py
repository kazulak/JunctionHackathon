from __future__ import annotations

from typing import Any

import stim

from qec_pipeline.measurements import measurement_order_from_stim_circuit


def build_repetition_code_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    """Build a Stim repetition-code memory circuit.

    This is the distilled pipeline version of the colleague repetition-code
    experiment in `qec_pipeline/rep_code_bundle`.
    """
    if basis != "memory_z":
        raise ValueError("repetition_code currently supports only basis: memory_z")

    distance = int(code["distance"])
    rounds = int(code["rounds"])
    if distance < 3 or distance % 2 == 0:
        raise ValueError("repetition_code distance must be odd and >= 3")
    if rounds < 1:
        raise ValueError("repetition_code rounds must be >= 1")

    stim_circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=distance,
        rounds=rounds,
        **_stim_noise_parameters(noise),
    )
    detector_model = stim_circuit.detector_error_model(decompose_errors=True)
    measurement_order = tuple(measurement_order_from_stim_circuit(stim_circuit))

    circuit_info = {
        "basis": basis,
        "code_family": "repetition_code",
        "stim_task": "repetition_code:memory",
        "distance": distance,
        "rounds": rounds,
        "requested_reset_mode": code.get("reset_mode", "reset"),
        "implemented_reset_mode": "active_reset",
        "num_qubits": stim_circuit.num_qubits,
        "num_measurements": stim_circuit.num_measurements,
        "num_detectors": stim_circuit.num_detectors,
        "num_observables": stim_circuit.num_observables,
        "num_ticks": sum(1 for instruction in stim_circuit if instruction.name == "TICK"),
        "noise_model": noise.get("model", "no_noise"),
        "noise_parameters": dict(noise.get("parameters", {})),
        "stim_noise_kwargs": _stim_noise_parameters(noise),
        "detector_model_num_errors": sum(
            1 for instruction in detector_model if instruction.type == "error"
        ),
    }

    return stim_circuit, detector_model, measurement_order, circuit_info


def _stim_noise_parameters(noise: dict[str, Any]) -> dict[str, float]:
    model = noise.get("model", "no_noise")
    if model in {"none", "no_noise", "iqm_calibration"}:
        return {}
    if model != "simple_depolarizing":
        raise NotImplementedError(f"Unsupported repetition-code noise model: {model}")

    parameters = noise.get("parameters", {}) or {}
    one_qubit_error = float(parameters.get("one_qubit_error", 0.0))
    two_qubit_error = float(parameters.get("two_qubit_error", one_qubit_error))
    return {
        "after_clifford_depolarization": max(one_qubit_error, two_qubit_error),
        "after_reset_flip_probability": float(parameters.get("reset_error", 0.0)),
        "before_measure_flip_probability": float(parameters.get("measurement_error", 0.0)),
        "before_round_data_depolarization": float(parameters.get("idle_error", 0.0)),
    }
