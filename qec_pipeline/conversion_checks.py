from __future__ import annotations

from typing import Callable

import numpy as np
import stim
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator

from qec_pipeline.conversion import stim_to_qiskit_minimal
from qec_pipeline.measurements import counts_to_measurement_array


def validate_conversion_metadata(
    stim_circuit: stim.Circuit,
    qiskit_circuit: QuantumCircuit,
    stim_to_dense: dict[int, int],
    measurement_order: list[int],
) -> list[str]:
    """Return human-readable conversion metadata problems."""
    problems = []

    if qiskit_circuit.num_qubits != len(stim_to_dense):
        problems.append(
            "Qiskit qubit count does not match dense Stim qubit map size: "
            f"{qiskit_circuit.num_qubits} != {len(stim_to_dense)}"
        )

    expected_dense_values = list(range(len(stim_to_dense)))
    if sorted(stim_to_dense.values()) != expected_dense_values:
        problems.append("Stim-to-dense map values are not contiguous 0..N-1.")

    if qiskit_circuit.num_clbits != stim_circuit.num_measurements:
        problems.append(
            "Qiskit classical bit count does not match Stim measurement count: "
            f"{qiskit_circuit.num_clbits} != {stim_circuit.num_measurements}"
        )

    if len(measurement_order) != stim_circuit.num_measurements:
        problems.append(
            "Measurement order length does not match Stim measurement count: "
            f"{len(measurement_order)} != {stim_circuit.num_measurements}"
        )

    return problems


def sample_stim_measurements(
    stim_circuit: stim.Circuit,
    shots: int,
    seed: int = 1,
) -> np.ndarray:
    """Sample Stim raw measurements as a boolean array."""
    return stim_circuit.compile_sampler(seed=seed).sample(shots).astype(bool)


def sample_qiskit_measurements(
    qiskit_circuit: QuantumCircuit,
    shots: int,
    seed: int = 1,
) -> np.ndarray:
    """Sample Qiskit raw measurements as a boolean array in clbit order."""
    backend = BasicSimulator()
    result = backend.run(
        qiskit_circuit,
        shots=shots,
        seed_simulator=seed,
    ).result()
    counts = result.get_counts()
    return counts_to_measurement_array(
        counts,
        num_measurements=qiskit_circuit.num_clbits,
        total_shots=shots,
    )


def convert_and_sample(
    stim_circuit: stim.Circuit,
    shots: int = 128,
    seed: int = 1,
    converter: Callable[[stim.Circuit], tuple] = stim_to_qiskit_minimal,
) -> tuple[np.ndarray, np.ndarray, QuantumCircuit, dict[int, int], list[int]]:
    """Convert one Stim circuit and sample both Stim and Qiskit versions."""
    qiskit_circuit, stim_to_dense, measurement_order = converter(stim_circuit)
    problems = validate_conversion_metadata(
        stim_circuit,
        qiskit_circuit,
        stim_to_dense,
        measurement_order,
    )
    if problems:
        raise AssertionError("\n".join(problems))

    stim_samples = sample_stim_measurements(stim_circuit, shots=shots, seed=seed)
    qiskit_samples = sample_qiskit_measurements(qiskit_circuit, shots=shots, seed=seed)

    return stim_samples, qiskit_samples, qiskit_circuit, stim_to_dense, measurement_order
