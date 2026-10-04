"""Mid-circuit measurement/reset probe (ERRATA E5).

Same qubits, coordinates, and hardware patch as the rotated surface code, but no
entangling gates: data qubits are prepared in |0> (memory_z) or |+> (memory_x)
and left alone while the ancillas repeat

    H, then one of: measure + reset | measure | nothing

for `rounds` cycles. Finally every data qubit is measured in its preparation
basis. Each data qubit has its own detector and observable, so the pipeline's
LER is the probability that *any* data qubit flipped. Comparing the three modes
on hardware separates "reset destroys neighbours" from "readout destroys
neighbours" (see baselines/post_hackathon/midcircuit_diagnosis_20261004).
"""

from __future__ import annotations

from typing import Any

import stim

from qec_pipeline.codes.surface_code import _count_detector_model_errors, count_flattened_ticks
from qec_pipeline.measurements import measurement_order_from_stim_circuit

PROBE_MODES = ("measure_reset", "measure", "none")


def build_midcircuit_probe_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    if basis not in {"memory_z", "memory_x"}:
        raise ValueError("midcircuit_probe supports basis memory_z or memory_x")
    mode = str(code.get("probe_mode", "measure_reset"))
    if mode not in PROBE_MODES:
        raise ValueError(f"probe_mode must be one of {PROBE_MODES}, got {mode!r}")
    if noise.get("model", "no_noise") not in {"no_noise", "none", "iqm_calibration"}:
        raise NotImplementedError("midcircuit_probe supports noise models no_noise and iqm_calibration")

    distance = int(code.get("distance", 3))
    rounds = int(code["rounds"])
    if rounds < 1:
        raise ValueError(f"Number of rounds must be >= 1. Got rounds={rounds}.")

    template = stim.Circuit.generated(f"surface_code:rotated_{basis}", distance=distance, rounds=1)
    flattened = list(template.flattened())
    coordinates = template.get_final_qubit_coordinates()
    ancillas = sorted({t.value for item in flattened if item.name == "MR" for t in item.targets_copy()})
    data = sorted(set(coordinates) - set(ancillas))

    circuit = stim.Circuit()
    for item in flattened:
        if item.name == "QUBIT_COORDS":
            circuit.append(item)
    if basis == "memory_z":
        circuit.append("R", data + ancillas)
    else:
        circuit.append("RX", data)
        circuit.append("R", ancillas)
    circuit.append("TICK")

    for _ in range(rounds):
        circuit.append("H", ancillas)
        circuit.append("TICK")
        if mode == "measure_reset":
            circuit.append("MR", ancillas)
        elif mode == "measure":
            circuit.append("M", ancillas)
        circuit.append("TICK")

    circuit.append("M" if basis == "memory_z" else "MX", data)
    for index, qubit in enumerate(data):
        record = stim.target_rec(index - len(data))
        circuit.append("DETECTOR", [record], list(coordinates[qubit]) + [rounds])
        circuit.append("OBSERVABLE_INCLUDE", [record], index)

    detector_model = circuit.detector_error_model(decompose_errors=True)
    circuit_info = {
        "basis": basis,
        "code_family": "midcircuit_probe",
        "probe_mode": mode,
        "mid_circuit_reset": "reset" if mode == "measure_reset" else "none",
        "distance": distance,
        "rounds": rounds,
        "data_qubits": data,
        "ancilla_qubits": ancillas,
        "num_qubits": circuit.num_qubits,
        "num_measurements": circuit.num_measurements,
        "num_detectors": circuit.num_detectors,
        "num_observables": circuit.num_observables,
        "num_ticks": count_flattened_ticks(circuit),
        "noise_model": noise.get("model", "no_noise"),
        "noise_parameters": dict(noise.get("parameters", {})),
        "detector_model_num_errors": _count_detector_model_errors(detector_model),
    }
    measurement_order = tuple(measurement_order_from_stim_circuit(circuit))
    return circuit, detector_model, measurement_order, circuit_info
