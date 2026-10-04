"""Mid-circuit reset strategies, encoded faithfully in the Stim circuit.

The same Stim circuit drives simulation, the decoder's detector error model, and the
hardware conversion, so the reset strategy must live here, not only in the converter.

Strategies (Gehér et al., "To reset, or not to reset - that is the question",
arXiv:2408.00758, Sec. I):

- "reset": unconditional reset after each ancilla measurement (Stim `MR`). On IQM
  hardware a Qiskit `reset` compiles to a second measurement plus a feedback pulse.
- "feedforward" (conditional reset): measure, then flip the ancilla back to |0>
  with an X conditioned on the recorded outcome (Stim `M` + `CX rec[-k] q`, IQM
  `cc_prx`). A readout *classification* error records the wrong bit AND applies the
  wrong flip, so it triggers detectors two rounds apart.
- "none" (no reset): measure only; the ancilla keeps its post-measurement state.
  The stabiliser outcome becomes m_j = n_{j-1} XOR n_j (paper Eq. 1), so every
  detector that referenced m_j is rewritten in terms of the raw outcomes n. A
  classification error again triggers detectors two rounds apart.

For memory experiments the paper finds no-reset and reset perform alike, provided
the decoder uses the matching detector error model, which this module guarantees.
"""

from __future__ import annotations

import stim

MID_CIRCUIT_RESET_STRATEGIES = ("reset", "feedforward", "none")
_NON_OPERATIONS = frozenset({"TICK", "DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"})


def apply_mid_circuit_reset(circuit: stim.Circuit, strategy: str) -> stim.Circuit:
    """Return `circuit` with every mid-circuit `MR`/`MRX` implemented by `strategy`."""
    if strategy not in MID_CIRCUIT_RESET_STRATEGIES:
        raise ValueError(f"mid_circuit_reset must be one of {MID_CIRCUIT_RESET_STRATEGIES}, got {strategy!r}")
    if strategy == "reset":
        return circuit

    instructions = list(circuit.flattened())
    used_later = _qubits_used_later(instructions)
    output = stim.Circuit()
    num_records = 0
    # Qubit -> raw record of its last no-reset measurement (the state it still carries).
    carried_record: dict[int, int] = {}
    # Raw record b -> raw record a such that the original outcome at b is n_b XOR n_a.
    partner: dict[int, int] = {}

    for index, instruction in enumerate(instructions):
        name = instruction.name

        if name in {"R", "RX"}:
            for qubit in _qubits(instruction):
                carried_record.pop(qubit, None)
            output.append(instruction)
            continue

        if name in {"DETECTOR", "OBSERVABLE_INCLUDE"}:
            output.append(_rewrite_record_references(instruction, num_records, partner))
            continue

        if name in {"M", "MX", "MY", "MR", "MRX", "MRY"}:
            qubits = _qubits(instruction)
            is_reset_measurement = name in {"MR", "MRX", "MRY"}
            measured_name = {"MR": "M", "MRX": "MX", "MRY": "MY"}.get(name, name)
            output.append(measured_name, instruction.targets_copy(), instruction.gate_args_copy())

            records = []
            for qubit in qubits:
                record = num_records
                num_records += 1
                records.append(record)
                if qubit in carried_record:
                    partner[record] = carried_record.pop(qubit)
                if is_reset_measurement and strategy == "none":
                    carried_record[qubit] = record

            if is_reset_measurement and strategy == "feedforward":
                feedback = []
                for offset, qubit in enumerate(qubits):
                    if qubit not in used_later[index]:
                        continue
                    if name != "MR":
                        raise NotImplementedError("feedforward reset is implemented for Z-basis MR only")
                    feedback += [stim.target_rec(offset - len(qubits)), stim.GateTarget(qubit)]
                if feedback:
                    output.append("CX", feedback)
            continue

        output.append(instruction)

    return output


def _rewrite_record_references(
    instruction: stim.CircuitInstruction,
    num_records: int,
    partner: dict[int, int],
) -> stim.CircuitInstruction:
    """Replace each reference to an original outcome by the raw outcomes it equals."""
    absolute: set[int] = set()
    for target in instruction.targets_copy():
        if not target.is_measurement_record_target:
            raise ValueError(f"Unexpected target in {instruction}")
        record = num_records + target.value
        expanded = {record, partner[record]} if record in partner else {record}
        absolute ^= expanded
    targets = [stim.target_rec(record - num_records) for record in sorted(absolute)]
    return stim.CircuitInstruction(instruction.name, targets, instruction.gate_args_copy())


def _qubits(instruction: stim.CircuitInstruction) -> list[int]:
    return [target.value for target in instruction.targets_copy() if target.is_qubit_target]


def _qubits_used_later(instructions: list[stim.CircuitInstruction]) -> list[set[int]]:
    used_later: list[set[int]] = [set() for _ in instructions]
    seen: set[int] = set()
    for index in range(len(instructions) - 1, -1, -1):
        used_later[index] = set(seen)
        if instructions[index].name not in _NON_OPERATIONS:
            seen.update(_qubits(instructions[index]))
    return used_later
