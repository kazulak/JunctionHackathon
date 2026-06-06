from __future__ import annotations

from typing import Any

import stim


def build_surface_code_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    """Build one Stim rotated surface-code memory circuit.

    Input:
        code: `config["code"]`
        noise: `config["noise"]`
        basis: "memory_z" or "memory_x"

    Output tuple:
        (stim_circuit, detector_model, measurement_order, circuit_info)
    """
    if code.get("family", "surface_code") != "surface_code":
        raise ValueError(f"surface-code builder received unsupported family: {code['family']}")
    if code.get("reset_mode", "reset") != "reset":
        raise NotImplementedError("surface-code no_reset circuits are not implemented yet")

    task = {
        "memory_z": "surface_code:rotated_memory_z",
        "memory_x": "surface_code:rotated_memory_x",
    }[basis]

    stim_circuit = stim.Circuit.generated(
        task,
        distance=int(code["distance"]),
        rounds=int(code["rounds"]),
        **_stim_noise_parameters(noise),
    )
    detector_model = stim_circuit.detector_error_model(decompose_errors=True)
    measurement_order = tuple(range(stim_circuit.num_measurements))
    circuit_info = {
        "basis": basis,
        "stim_task": task,
        "num_qubits": stim_circuit.num_qubits,
        "num_measurements": stim_circuit.num_measurements,
        "num_detectors": stim_circuit.num_detectors,
        "num_observables": stim_circuit.num_observables,
        "num_ticks": sum(1 for instruction in stim_circuit if instruction.name == "TICK"),
        "noise_model": noise["model"],
    }

    return stim_circuit, detector_model, measurement_order, circuit_info


def _stim_noise_parameters(noise: dict[str, Any]) -> dict[str, float]:
    if noise["model"] in {"none", "no_noise"}:
        return {}

    if noise["model"] != "simple_depolarizing":
        raise NotImplementedError(f"{noise['model']} Stim noise parameters")

    parameters = noise.get("parameters", {})
    return {
        "after_clifford_depolarization": float(parameters.get("one_qubit_error", 0.0)),
        "after_reset_flip_probability": float(parameters.get("reset_error", 0.0)),
        "before_measure_flip_probability": float(parameters.get("measurement_error", 0.0)),
        "before_round_data_depolarization": float(parameters.get("idle_error", 0.0)),
    }
