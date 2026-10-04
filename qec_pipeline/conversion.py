from __future__ import annotations

import stim
from qiskit import QuantumCircuit


def stim_to_qiskit_minimal(
    stim_circuit: stim.Circuit,
    omit_initial_resets: bool = False,
    group_measurements: bool = True,
) -> tuple:
    """Convert a Stim memory circuit to Qiskit, instruction by instruction.

    The Stim circuit is the single source of truth: the mid-circuit reset strategy
    (see `qec_pipeline.codes.reset_strategies`) is already encoded in it, and this
    converter only translates.

    - `MR` / `MRX`: measure, then Qiskit `reset` for qubits used later. On IQM a
      `reset` compiles to a *second* measurement plus a feedback pulse.
    - `M` / `MX`: measure only.
    - `CX rec[-k] q` (Stim classical control): an X on `q` conditioned on that
      measurement result (`if_test`, IQM `cc_prx`).

    With `group_measurements` (default) every measurement instruction is emitted as
    one block between barriers. IQM multiplexes consecutive measurements into one
    readout window only when no other operation on those qubits sits between them;
    emitting `measure, reset, measure, reset, ...` serializes the readouts.

    Output:
        (qiskit_circuit, stim_to_dense, measurement_order)
    """
    flat = list(stim_circuit.flattened())
    initial_reset_instruction_indices = (
        _initial_reset_instruction_indices(flat) if omit_initial_resets else set()
    )
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
    measurement_order: list[int] = []

    instruction_index = -1
    while instruction_index + 1 < len(flat):
        instruction_index += 1
        instruction = flat[instruction_index]
        name = instruction.name
        if name in _STIM_SKIP:
            continue

        if name in {"CX", "CZ"}:
            _two_qubit_or_controlled(qiskit_circuit, instruction, stim_to_dense, measurement_index)
            continue

        targets = _qubit_targets(instruction)
        dense_targets = [stim_to_dense[target] for target in targets]

        if name == "R":
            if instruction_index not in initial_reset_instruction_indices:
                for qubit in dense_targets:
                    qiskit_circuit.reset(qubit)

        elif name == "RX":
            for qubit in dense_targets:
                if instruction_index not in initial_reset_instruction_indices:
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

        elif name in {"M", "MX", "MR", "MRX"}:
            # Merge immediately following measurements of the same kind (the noise model
            # emits one instruction per qubit) so they form one multiplexed readout block.
            while (
                instruction_index + 1 < len(flat)
                and flat[instruction_index + 1].name == name
                and not set(_qubit_targets(flat[instruction_index + 1])) & set(targets)
            ):
                instruction_index += 1
                targets = targets + _qubit_targets(flat[instruction_index])
            dense_targets = [stim_to_dense[target] for target in targets]
            measurement_index = _measurement_block(
                qiskit_circuit,
                targets,
                dense_targets,
                basis="x" if name in {"MX", "MRX"} else "z",
                reset=name in {"MR", "MRX"},
                measurement_index=measurement_index,
                measurement_order=measurement_order,
                future_qubits=future_qubits[instruction_index],
                group_measurements=group_measurements,
            )

        else:
            raise NotImplementedError(f"Stim instruction not supported in Qiskit converter: {name}")

    if measurement_index != stim_circuit.num_measurements:
        raise ValueError(
            "Converted measurement count does not match Stim measurement count: "
            f"{measurement_index} != {stim_circuit.num_measurements}"
        )

    return qiskit_circuit, stim_to_dense, measurement_order


def _two_qubit_or_controlled(
    qiskit_circuit: QuantumCircuit,
    instruction: stim.CircuitInstruction,
    stim_to_dense: dict[int, int],
    measurement_index: int,
) -> None:
    targets = instruction.targets_copy()
    if len(targets) % 2 != 0:
        raise ValueError(f"Stim instruction {instruction.name} requires an even number of targets")
    for index in range(0, len(targets), 2):
        control, target = targets[index], targets[index + 1]
        if control.is_measurement_record_target:
            if instruction.name != "CX" or not target.is_qubit_target:
                raise NotImplementedError(
                    "Only classically controlled X (Stim `CX rec[-k] q`) is supported; IQM can "
                    f"condition only X-type rotations. Got: {instruction}"
                )
            clbit = qiskit_circuit.clbits[measurement_index + control.value]
            with qiskit_circuit.if_test((clbit, 1)):
                qiskit_circuit.x(stim_to_dense[target.value])
            continue
        if not (control.is_qubit_target and target.is_qubit_target):
            raise NotImplementedError(f"Unsupported targets in {instruction}")
        if instruction.name == "CX":
            qiskit_circuit.cx(stim_to_dense[control.value], stim_to_dense[target.value])
        else:
            qiskit_circuit.cz(stim_to_dense[control.value], stim_to_dense[target.value])


def _measurement_block(
    qiskit_circuit: QuantumCircuit,
    stim_targets: list[int],
    dense_targets: list[int],
    basis: str,
    reset: bool,
    measurement_index: int,
    measurement_order: list[int],
    future_qubits: set[int],
    group_measurements: bool,
) -> int:
    """Measure all targets of one Stim instruction as a single (multiplexable) block."""
    if len(set(stim_targets)) != len(stim_targets):
        raise NotImplementedError("Repeated targets inside one measurement instruction are not supported")

    if basis == "x":
        for qubit in dense_targets:
            qiskit_circuit.h(qubit)
    if group_measurements:
        qiskit_circuit.barrier(dense_targets)
    for stim_qubit, dense_qubit in zip(stim_targets, dense_targets, strict=True):
        qiskit_circuit.measure(dense_qubit, measurement_index)
        measurement_order.append(stim_qubit)
        measurement_index += 1
    if group_measurements:
        qiskit_circuit.barrier(dense_targets)

    for stim_qubit, dense_qubit in zip(stim_targets, dense_targets, strict=True):
        if stim_qubit not in future_qubits:
            continue
        if reset:
            qiskit_circuit.reset(dense_qubit)
        if basis == "x":
            # MX leaves the measured X eigenstate and MRX leaves |+>; Qiskit's
            # H + Z-measurement leaves a Z eigenstate, so rotate back.
            qiskit_circuit.h(dense_qubit)
    return measurement_index


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


def _initial_reset_instruction_indices(instructions: list[stim.CircuitInstruction]) -> set[int]:
    indices = set()
    for index, instruction in enumerate(instructions):
        name = instruction.name
        if name in _STIM_SKIP:
            continue
        if name in {"R", "RX"}:
            indices.add(index)
            continue
        break
    return indices


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
