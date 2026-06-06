from __future__ import annotations

import stim
from qiskit import QuantumCircuit


def stim_to_qiskit_minimal(stim_circuit: stim.Circuit) -> tuple:
    """Convert our generated Stim memory circuit to Qiskit.

    OUR ADDITION.

    Why this exists:
        The challenge-provided `surface_code.stim_to_qiskit` is useful, but the
        current Stim-generated memory-X circuit contains X-basis instructions
        such as `RX` and `MX`. This minimal converter supports those instructions
        so the same baseline pipeline can run `basis: both`.

    Output:
        (qiskit_circuit, stim_to_dense, measurement_order)
    """
    flat = stim_circuit.flattened()
    all_stim_qubits = sorted(
        {
            target.value
            for instruction in flat
            for target in instruction.targets_copy()
            if target.is_qubit_target
        }
    )
    stim_to_dense = {stim_qubit: index for index, stim_qubit in enumerate(all_stim_qubits)}
    qiskit_circuit = QuantumCircuit(len(all_stim_qubits), stim_circuit.num_measurements)

    measurement_index = 0
    measurement_order = []

    for instruction in flat:
        name = instruction.name
        if name in _STIM_SKIP:
            continue

        targets = [target.value for target in instruction.targets_copy() if target.is_qubit_target]
        dense_targets = [stim_to_dense[target] for target in targets]

        if name == "R":
            for qubit in dense_targets:
                qiskit_circuit.reset(qubit)

        elif name == "RX":
            for qubit in dense_targets:
                qiskit_circuit.reset(qubit)
                qiskit_circuit.h(qubit)

        elif name == "H":
            for qubit in dense_targets:
                qiskit_circuit.h(qubit)

        elif name == "X":
            for qubit in dense_targets:
                qiskit_circuit.x(qubit)

        elif name == "Z":
            for qubit in dense_targets:
                qiskit_circuit.z(qubit)

        elif name == "CX":
            for i in range(0, len(dense_targets), 2):
                qiskit_circuit.cx(dense_targets[i], dense_targets[i + 1])

        elif name == "CZ":
            for i in range(0, len(dense_targets), 2):
                qiskit_circuit.cz(dense_targets[i], dense_targets[i + 1])

        elif name == "M":
            measurement_index = _measure_z(
                qiskit_circuit,
                targets,
                dense_targets,
                measurement_index,
                measurement_order,
            )

        elif name == "MX":
            for qubit in dense_targets:
                qiskit_circuit.h(qubit)
            measurement_index = _measure_z(
                qiskit_circuit,
                targets,
                dense_targets,
                measurement_index,
                measurement_order,
            )

        elif name == "MR":
            measurement_index = _measure_z(
                qiskit_circuit,
                targets,
                dense_targets,
                measurement_index,
                measurement_order,
            )
            for qubit in dense_targets:
                qiskit_circuit.reset(qubit)

        elif name == "MRX":
            for qubit in dense_targets:
                qiskit_circuit.h(qubit)
            measurement_index = _measure_z(
                qiskit_circuit,
                targets,
                dense_targets,
                measurement_index,
                measurement_order,
            )
            for qubit in dense_targets:
                qiskit_circuit.reset(qubit)
                qiskit_circuit.h(qubit)

        else:
            raise NotImplementedError(f"Stim instruction not supported in Qiskit converter: {name}")

    return qiskit_circuit, stim_to_dense, measurement_order


def _measure_z(
    qiskit_circuit: QuantumCircuit,
    stim_targets: list[int],
    dense_targets: list[int],
    measurement_index: int,
    measurement_order: list[int],
) -> int:
    for stim_qubit, dense_qubit in zip(stim_targets, dense_targets):
        qiskit_circuit.measure(dense_qubit, measurement_index)
        measurement_order.append(stim_qubit)
        measurement_index += 1
    return measurement_index


_STIM_SKIP = frozenset(
    {
        "QUBIT_COORDS",
        "TICK",
        "DETECTOR",
        "OBSERVABLE_INCLUDE",
        "SHIFT_COORDS",
        "DEPOLARIZE1",
        "DEPOLARIZE2",
        "X_ERROR",
        "Y_ERROR",
        "Z_ERROR",
        "PAULI_CHANNEL_1",
        "PAULI_CHANNEL_2",
        "CORRELATED_ERROR",
        "ELSE_CORRELATED_ERROR",
    }
)
