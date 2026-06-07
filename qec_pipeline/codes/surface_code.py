from __future__ import annotations

from typing import Any
import warnings

import stim

from qec_pipeline.measurements import measurement_order_from_stim_circuit


def build_surface_code_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    """Build one working Stim rotated surface-code memory circuit.

    Input:
        code: config["code"]
        noise: config["noise"]
        basis: "memory_z" or "memory_x"

    Output:
        (stim_circuit, detector_model, measurement_order, circuit_info)

    Important:
        This implementation intentionally uses the standard Stim-generated
        active-reset rotated memory circuit.

        If config requests no_reset / no_active_reset, we do NOT implement it
        here. We warn and fall back to active reset, because the no-reset
        version is currently experimentally unstable / near-random.
    """

    _validate_basis(basis)
    _validate_code_family(code)

    distance = int(code["distance"])
    rounds = int(code["rounds"])

    _validate_distance(distance)
    _validate_rounds(rounds)

    requested_reset_mode = str(code.get("reset_mode", "reset")).lower()

    force_active_reset = requested_reset_mode in {
        "no_reset",
        "no-reset",
        "no_active_reset",
        "no-active-reset",
        "none",
        "false",
    }

    if force_active_reset:
        warnings.warn(
            f"Requested reset_mode={requested_reset_mode!r}, but this builder "
            "does not implement no-reset surface-code circuits. Falling back "
            "to standard active-reset Stim rotated memory circuit.",
            RuntimeWarning,
        )

    task = _stim_task_for_basis(basis)
    noise_kwargs = _stim_noise_parameters(noise)

    stim_circuit = stim.Circuit.generated(
        task,
        distance=distance,
        rounds=rounds,
        **noise_kwargs,
    )

    _validate_generated_circuit(stim_circuit)

    detector_model = stim_circuit.detector_error_model(decompose_errors=True)

    measurement_order = tuple(measurement_order_from_stim_circuit(stim_circuit))

    circuit_info = {
        "basis": basis,
        "stim_task": task,
        "distance": distance,
        "rounds": rounds,

        "requested_reset_mode": requested_reset_mode,
        "implemented_reset_mode": "active_reset",
        "forced_active_reset": force_active_reset,

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


def _stim_task_for_basis(basis: str) -> str:
    if basis == "memory_z":
        return "surface_code:rotated_memory_z"

    if basis == "memory_x":
        return "surface_code:rotated_memory_x"

    raise ValueError(
        f"Unsupported basis {basis!r}. Expected 'memory_z' or 'memory_x'."
    )


def _validate_basis(basis: str) -> None:
    if basis not in {"memory_z", "memory_x"}:
        raise ValueError(
            f"Unsupported basis {basis!r}. Expected 'memory_z' or 'memory_x'."
        )


def _validate_code_family(code: dict[str, Any]) -> None:
    family = code.get("family", "surface_code")

    if family != "surface_code":
        raise ValueError(
            f"Unsupported code family {family!r}. Only 'surface_code' works here."
        )


def _validate_distance(distance: int) -> None:
    if distance < 3:
        raise ValueError(
            f"Surface-code distance must be >= 3. Got distance={distance}."
        )

    if distance % 2 == 0:
        raise ValueError(
            f"Rotated surface-code distance should be odd. Got distance={distance}."
        )


def _validate_rounds(rounds: int) -> None:
    if rounds < 1:
        raise ValueError(f"Number of rounds must be >= 1. Got rounds={rounds}.")


def _stim_noise_parameters(noise: dict[str, Any]) -> dict[str, float]:
    """Map your existing YAML noise fields to Stim generated-circuit knobs.

    No YAML changes required.

    Stim's built-in generated surface-code circuit has one shared Clifford
    depolarization parameter. It does not distinguish 1Q and 2Q depolarization
    here, so we use max(one_qubit_error, two_qubit_error) instead of silently
    ignoring two_qubit_error.
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

    clifford_error = max(one_qubit_error, two_qubit_error)

    reset_error = float(parameters.get("reset_error", 0.0))
    measurement_error = float(parameters.get("measurement_error", 0.0))
    idle_error = float(parameters.get("idle_error", 0.0))

    _validate_probability("one_qubit_error", one_qubit_error)
    _validate_probability("two_qubit_error", two_qubit_error)
    _validate_probability("clifford_error", clifford_error)
    _validate_probability("reset_error", reset_error)
    _validate_probability("measurement_error", measurement_error)
    _validate_probability("idle_error", idle_error)

    return {
        "after_clifford_depolarization": clifford_error,
        "after_reset_flip_probability": reset_error,
        "before_measure_flip_probability": measurement_error,
        "before_round_data_depolarization": idle_error,
    }


def _validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]. Got {value}.")


def _validate_generated_circuit(stim_circuit: stim.Circuit) -> None:
    if stim_circuit.num_qubits <= 0:
        raise RuntimeError("Generated circuit has zero qubits.")

    if stim_circuit.num_measurements <= 0:
        raise RuntimeError("Generated circuit has zero measurements.")

    if stim_circuit.num_detectors <= 0:
        raise RuntimeError("Generated circuit has zero detectors.")

    if stim_circuit.num_observables <= 0:
        raise RuntimeError("Generated circuit has zero logical observables.")


def _count_top_level_ticks(circuit: stim.Circuit) -> int:
    return sum(1 for instruction in circuit if instruction.name == "TICK")


def _count_detector_model_errors(
    detector_model: stim.DetectorErrorModel,
) -> int:
    return sum(
        1
        for instruction in detector_model
        if instruction.type == "error"
    )
