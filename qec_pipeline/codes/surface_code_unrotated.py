from __future__ import annotations

from typing import Any

import stim

from qec_pipeline.codes.surface_code import (
    _count_detector_model_errors,
    _count_top_level_ticks,
    _stim_noise_parameters,
)
from qec_pipeline.measurements import measurement_order_from_stim_circuit


def build_unrotated_surface_code_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    """Build Stim's unrotated surface-code memory circuit."""
    if basis == "memory_z":
        task = "surface_code:unrotated_memory_z"
    elif basis == "memory_x":
        task = "surface_code:unrotated_memory_x"
    else:
        raise ValueError("unrotated surface code supports basis memory_z or memory_x")

    distance = int(code["distance"])
    rounds = int(code["rounds"])
    if distance < 3:
        raise ValueError(f"Surface-code distance must be >= 3. Got distance={distance}.")
    if rounds < 1:
        raise ValueError(f"Number of rounds must be >= 1. Got rounds={rounds}.")

    noise_kwargs = _stim_noise_parameters(noise)
    stim_circuit = stim.Circuit.generated(
        task,
        distance=distance,
        rounds=rounds,
        **noise_kwargs,
    )
    detector_model = stim_circuit.detector_error_model(decompose_errors=True)
    measurement_order = tuple(measurement_order_from_stim_circuit(stim_circuit))
    circuit_info = {
        "basis": basis,
        "stim_task": task,
        "code_family": "surface_code_unrotated",
        "surface_code_variant": "unrotated",
        "distance": distance,
        "rounds": rounds,
        "requested_reset_mode": str(code.get("reset_mode", "reset")).lower(),
        "implemented_reset_mode": "active_reset",
        "forced_active_reset": False,
        "num_qubits": stim_circuit.num_qubits,
        "num_measurements": stim_circuit.num_measurements,
        "num_detectors": stim_circuit.num_detectors,
        "num_observables": stim_circuit.num_observables,
        "num_ticks": _count_top_level_ticks(stim_circuit),
        "noise_model": noise.get("model", "no_noise"),
        "noise_parameters": dict(noise.get("parameters", {})),
        "stim_noise_kwargs": noise_kwargs,
        "detector_model_num_errors": _count_detector_model_errors(detector_model),
    }

    return stim_circuit, detector_model, measurement_order, circuit_info
