from __future__ import annotations

from qec_pipeline.config import CodeConfig, NoiseConfig
from qec_pipeline.types import CircuitBundle


def build_surface_code_circuit(
    code: CodeConfig,
    noise: NoiseConfig | None = None,
) -> CircuitBundle:
    """Build a rotated surface-code memory experiment.

    Input:
        code: distance, rounds, memory basis, reset mode.
        noise: optional noise model config for simulator/decoder graph.

    Output:
        CircuitBundle with:
        - source_circuit: Stim circuit with coordinates, detectors, observables.
        - hardware_circuit: Qiskit circuit for IQM after conversion.
        - detector_model: Stim detector error model for decoder construction.
        - metadata: qubit counts, detector counts, logical observable info.

    Implementation notes:
        Start from Stim generated circuits for MVP. Later replace or extend with
        custom schedules, no-reset variants, and IQM-native optimizations.
    """
    if code.distance < 3 or code.distance % 2 == 0:
        raise ValueError("Toy surface-code demo expects an odd distance >= 3.")
    if code.rounds < 1:
        raise ValueError("rounds must be positive")

    data_qubits = code.distance * code.distance
    ancilla_qubits = data_qubits - 1
    num_measurements = ancilla_qubits * code.rounds + data_qubits
    num_detectors = ancilla_qubits * code.rounds
    num_observables = 1

    source_circuit = {
        "kind": "toy_surface_code",
        "family": code.family,
        "distance": code.distance,
        "rounds": code.rounds,
        "basis": code.basis,
        "reset_mode": code.reset_mode,
        "noise": None if noise is None else noise.model,
    }

    return CircuitBundle(
        source_circuit=source_circuit,
        hardware_circuit=None,
        detector_model=None,
        measurement_order=tuple(range(num_measurements)),
        metadata={
            "is_toy_demo": True,
            "num_data_qubits": data_qubits,
            "num_ancilla_qubits": ancilla_qubits,
            "num_qubits": data_qubits + ancilla_qubits,
            "num_measurements": num_measurements,
            "num_detectors": num_detectors,
            "num_observables": num_observables,
            "note": "Toy no-noise circuit metadata only; not a real Stim/Qiskit circuit.",
        },
    )
