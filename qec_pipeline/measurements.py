from __future__ import annotations

import numpy as np
import stim


def counts_to_measurement_array(
    counts: dict[str, int],
    num_measurements: int,
    total_shots: int,
) -> np.ndarray:
    """Convert Qiskit counts into a boolean array ordered by classical bit index."""
    result = np.zeros((total_shots, num_measurements), dtype=bool)
    row_index = 0

    for bitstring, count in counts.items():
        bits_by_clbit = bitstring.replace(" ", "")[::-1]
        if len(bits_by_clbit) < num_measurements:
            raise ValueError(
                "Qiskit bitstring is shorter than requested measurement count: "
                f"{len(bits_by_clbit)} < {num_measurements}"
            )

        row = np.array(
            [bit == "1" for bit in bits_by_clbit[:num_measurements]],
            dtype=bool,
        )
        for _ in range(count):
            if row_index >= total_shots:
                raise ValueError("Counts contain more shots than total_shots")
            result[row_index] = row
            row_index += 1

    if row_index != total_shots:
        raise ValueError(f"Counts contain {row_index} shots, expected {total_shots}")

    return result


def virtualize_omitted_repeated_resets(
    measurements: np.ndarray,
    measurement_order: list[int] | tuple[int, ...],
) -> np.ndarray:
    """Convert no-reset repeated ancilla records into reset-style records.

    If an ancilla is measured and reused without an active reset, its next raw
    measurement includes the previous measured state. XOR with the previous
    physical measurement gives the virtual result expected by the Stim circuit
    that used `MR`.
    """
    result = measurements.copy()
    previous_index_by_qubit = {}
    for index, stim_qubit in enumerate(measurement_order):
        previous_index = previous_index_by_qubit.get(stim_qubit)
        if previous_index is not None:
            result[:, index] = measurements[:, index] ^ measurements[:, previous_index]
        previous_index_by_qubit[stim_qubit] = index
    return result


def measurement_order_from_stim_circuit(stim_circuit: stim.Circuit) -> list[int]:
    """Return the measured Stim qubit for each measurement-record index."""
    order = []
    for instruction in stim_circuit.flattened():
        if instruction.name not in {"M", "MX", "MY", "MR", "MRX", "MRY"}:
            continue
        order.extend(
            target.value
            for target in instruction.targets_copy()
            if target.is_qubit_target
        )

    if len(order) != stim_circuit.num_measurements:
        raise ValueError(
            "Measurement-order extraction failed: "
            f"{len(order)} targets != {stim_circuit.num_measurements} measurements"
        )

    return order
