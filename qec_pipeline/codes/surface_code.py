from __future__ import annotations

from typing import Any

import stim

from qec_pipeline.codes.reset_strategies import apply_mid_circuit_reset
from qec_pipeline.measurements import measurement_order_from_stim_circuit
from qec_pipeline.stim_utils import count_detector_model_errors, count_flattened_ticks

NO_NOISE = {"model": "no_noise", "parameters": {}}


def build_surface_code_circuit(code: dict[str, Any], noise: dict[str, Any], basis: str) -> tuple:
    """Stim's rotated surface-code memory circuit, with `simple_depolarizing` noise if configured.

    Output: (stim_circuit, detector_model, measurement_order, circuit_info).
    The mid-circuit reset strategy (`code.mid_circuit_reset`) is encoded in the circuit.
    """
    return _build(code, noise, basis, family="surface_code", variant="rotated", stim_noise=noise)


def build_iqm_surface_code_circuit(code: dict[str, Any], noise: dict[str, Any], basis: str) -> tuple:
    """Rotated surface code built noise-free: calibration noise is injected after mapping."""
    return _build(code, noise, basis, family="surface_code_iqm", variant="rotated", stim_noise=NO_NOISE)


def build_unrotated_surface_code_circuit(code: dict[str, Any], noise: dict[str, Any], basis: str) -> tuple:
    """Stim's unrotated surface-code memory circuit."""
    return _build(code, noise, basis, family="surface_code_unrotated", variant="unrotated", stim_noise=noise)


def _build(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
    family: str,
    variant: str,
    stim_noise: dict[str, Any],
) -> tuple:
    if basis not in {"memory_z", "memory_x"}:
        raise ValueError(f"Unsupported basis {basis!r}. Expected 'memory_z' or 'memory_x'.")
    distance = int(code["distance"])
    rounds = int(code["rounds"])
    if distance < 3:
        raise ValueError(f"Surface-code distance must be >= 3. Got distance={distance}.")
    if variant == "rotated" and distance % 2 == 0:
        raise ValueError(f"Rotated surface-code distance should be odd. Got distance={distance}.")
    if rounds < 1:
        raise ValueError(f"Number of rounds must be >= 1. Got rounds={rounds}.")

    task = f"surface_code:{variant}_{basis}"
    noise_kwargs = _stim_noise_parameters(stim_noise)
    stim_circuit = stim.Circuit.generated(task, distance=distance, rounds=rounds, **noise_kwargs)
    mid_circuit_reset = str(code.get("mid_circuit_reset", "reset"))
    stim_circuit = apply_mid_circuit_reset(stim_circuit, mid_circuit_reset)
    detector_model = stim_circuit.detector_error_model(decompose_errors=True)

    circuit_info = {
        "basis": basis,
        "stim_task": task,
        "code_family": family,
        "surface_code_variant": variant,
        "distance": distance,
        "rounds": rounds,
        "mid_circuit_reset": mid_circuit_reset,
        "num_qubits": stim_circuit.num_qubits,
        "num_measurements": stim_circuit.num_measurements,
        "num_detectors": stim_circuit.num_detectors,
        "num_observables": stim_circuit.num_observables,
        "num_ticks": count_flattened_ticks(stim_circuit),
        "noise_model": noise.get("model", "no_noise"),
        "noise_parameters": dict(noise.get("parameters", {})),
        "stim_noise_kwargs": noise_kwargs,
        "detector_model_num_errors": count_detector_model_errors(detector_model),
    }
    measurement_order = tuple(measurement_order_from_stim_circuit(stim_circuit))
    return stim_circuit, detector_model, measurement_order, circuit_info


def _stim_noise_parameters(noise: dict[str, Any]) -> dict[str, float]:
    """Map `simple_depolarizing` YAML fields to Stim's generated-circuit noise knobs.

    Stim's generated circuits have one shared Clifford depolarization parameter, so
    max(one_qubit_error, two_qubit_error) is used rather than silently dropping one.
    `iqm_calibration` noise is injected later, per qubit, after mapping.
    """
    model = noise.get("model", "no_noise")
    if model in {"none", "no_noise", "iqm_calibration"}:
        return {}
    if model != "simple_depolarizing":
        raise NotImplementedError(
            f"Unsupported noise model {model!r}. "
            "Supported: 'no_noise', 'none', 'simple_depolarizing', 'iqm_calibration'."
        )

    parameters = noise.get("parameters", {})
    one_qubit_error = float(parameters.get("one_qubit_error", 0.0))
    two_qubit_error = float(parameters.get("two_qubit_error", one_qubit_error))
    knobs = {
        "after_clifford_depolarization": max(one_qubit_error, two_qubit_error),
        "after_reset_flip_probability": float(parameters.get("reset_error", 0.0)),
        "before_measure_flip_probability": float(parameters.get("measurement_error", 0.0)),
        "before_round_data_depolarization": float(parameters.get("idle_error", 0.0)),
    }
    for name, value in {"one_qubit_error": one_qubit_error, "two_qubit_error": two_qubit_error, **knobs}.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]. Got {value}.")
    return knobs
