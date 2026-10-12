"""Small helpers for walking Stim circuits, shared by every pipeline stage."""

from __future__ import annotations

from collections.abc import Iterable

import stim

# Instructions that annotate a circuit without acting on qubits.
ANNOTATIONS = frozenset({"TICK", "DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"})
NOISE_CHANNELS = frozenset(
    {
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
MEASUREMENTS = frozenset({"M", "MX", "MY", "MR", "MRX", "MRY"})


def qubit_targets(instruction: stim.CircuitInstruction) -> list[int]:
    """Qubit indices an instruction acts on (measurement-record targets are skipped)."""
    return [target.value for target in instruction.targets_copy() if target.is_qubit_target]


def stim_to_dense(stim_circuit: stim.Circuit) -> dict[int, int]:
    """Map each Stim qubit the circuit uses to a dense 0..N-1 index (the Qiskit qubit order)."""
    active = sorted({qubit for instruction in stim_circuit.flattened() for qubit in qubit_targets(instruction)})
    return {stim_qubit: index for index, stim_qubit in enumerate(active)}


def qubits_used_later(
    instructions: list[stim.CircuitInstruction],
    ignored: Iterable[str] = ANNOTATIONS,
) -> list[set[int]]:
    """For each instruction, the qubits touched by any later instruction not in `ignored`."""
    ignored = frozenset(ignored)
    used_later: list[set[int]] = [set() for _ in instructions]
    seen: set[int] = set()
    for index in range(len(instructions) - 1, -1, -1):
        used_later[index] = set(seen)
        if instructions[index].name not in ignored:
            seen.update(qubit_targets(instructions[index]))
    return used_later


def count_flattened_ticks(circuit: stim.Circuit) -> int:
    """Count TICKs in the fully unrolled circuit, including those inside REPEAT blocks."""
    return sum(1 for instruction in circuit.flattened() if instruction.name == "TICK")


def count_detector_model_errors(detector_model: stim.DetectorErrorModel) -> int:
    return sum(1 for instruction in detector_model if instruction.type == "error")
