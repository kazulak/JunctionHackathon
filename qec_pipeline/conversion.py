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
    flat = list(stim_circuit.flattened())
    future_qubits = _future_executable_qubits(flat)
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

    for instruction_index, instruction in enumerate(flat):
        name = instruction.name
        if name in _STIM_SKIP:
            continue

        targets = _qubit_targets(instruction)
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
            _require_even_targets(name, dense_targets)
            for i in range(0, len(dense_targets), 2):
                qiskit_circuit.cx(dense_targets[i], dense_targets[i + 1])

        elif name == "CZ":
            _require_even_targets(name, dense_targets)
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
            measurement_index = _measure_x(
                qiskit_circuit,
                targets,
                dense_targets,
                measurement_index,
                measurement_order,
                future_qubits[instruction_index],
            )

        elif name == "MR":
            for stim_qubit, dense_qubit in zip(targets, dense_targets):
                qiskit_circuit.measure(dense_qubit, measurement_index)
                measurement_order.append(stim_qubit)
                measurement_index += 1
                qiskit_circuit.reset(dense_qubit)

        elif name == "MRX":
            for stim_qubit, dense_qubit in zip(targets, dense_targets):
                qiskit_circuit.h(dense_qubit)
                qiskit_circuit.measure(dense_qubit, measurement_index)
                measurement_order.append(stim_qubit)
                measurement_index += 1
                qiskit_circuit.reset(dense_qubit)
                qiskit_circuit.h(dense_qubit)

        else:
            raise NotImplementedError(f"Stim instruction not supported in Qiskit converter: {name}")

    if measurement_index != stim_circuit.num_measurements:
        raise ValueError(
            "Converted measurement count does not match Stim measurement count: "
            f"{measurement_index} != {stim_circuit.num_measurements}"
        )

    return qiskit_circuit, stim_to_dense, measurement_order


def _qubit_targets(instruction: stim.CircuitInstruction) -> list[int]:
    targets = []
    for target in instruction.targets_copy():
        if not target.is_qubit_target:
            continue
        if target.is_inverted_result_target:
            raise ValueError(
                "Inverted measurement target is not supported by the Qiskit converter yet: "
                f"{instruction}"
            )
        targets.append(target.value)
    return targets


def _require_even_targets(name: str, dense_targets: list[int]) -> None:
    if len(dense_targets) % 2 != 0:
        raise ValueError(f"Stim instruction {name} requires an even number of qubit targets")


def _future_executable_qubits(instructions: list[stim.CircuitInstruction]) -> list[set[int]]:
    future: list[set[int]] = [set() for _ in instructions]
    seen_later: set[int] = set()

    for index in range(len(instructions) - 1, -1, -1):
        future[index] = set(seen_later)
        instruction = instructions[index]
        if instruction.name in _STIM_SKIP:
            continue
        for target in instruction.targets_copy():
            if target.is_qubit_target:
                seen_later.add(target.value)

    return future


def _measure_x(
    qiskit_circuit: QuantumCircuit,
    stim_targets: list[int],
    dense_targets: list[int],
    measurement_index: int,
    measurement_order: list[int],
    future_qubits: set[int],
) -> int:
    for index, (stim_qubit, dense_qubit) in enumerate(zip(stim_targets, dense_targets)):
        qiskit_circuit.h(dense_qubit)
        qiskit_circuit.measure(dense_qubit, measurement_index)
        measurement_order.append(stim_qubit)
        measurement_index += 1

        # Stim's MX leaves the qubit in the measured X eigenstate. Qiskit's
        # H+Z-measurement leaves it in the Z eigenstate, so restore only when
        # later instructions can observe the post-measurement state.
        if stim_qubit in future_qubits or stim_qubit in stim_targets[index + 1 :]:
            qiskit_circuit.h(dense_qubit)

    return measurement_index


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
