from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import stim
import yaml

from qec_pipeline.codes.surface_code import count_flattened_ticks
from qec_pipeline.mapping import parse_hardware_calibration


def apply_iqm_calibration_noise(
    circuit: tuple,
    noise: dict[str, Any],
    mapping: dict[str, Any],
) -> tuple:
    """Inject per-qubit/per-coupler IQM calibration noise into a Stim circuit."""
    stim_circuit, _detector_model, measurement_order, circuit_info = circuit
    mapping_info = circuit_info.get("mapping")
    if mapping_info is None:
        raise ValueError("noise.model=iqm_calibration requires a selected mapping")

    calibration_file = noise.get("calibration_file") or mapping.get("calibration_file")
    if not calibration_file:
        raise ValueError("noise.model=iqm_calibration requires noise.calibration_file or mapping.calibration_file")

    calibration = yaml.safe_load(Path(calibration_file).read_text(encoding="utf-8")) or {}
    hardware = parse_hardware_calibration(
        calibration,
        exclude_qubits=(mapping.get("options", {}) or {}).get("exclude_qubits", []),
    )

    options = noise.get("options", {}) or {}
    noise_builder = _IqmNoiseBuilder(
        hardware=hardware,
        mapping_info=mapping_info,
        rounds=int(circuit_info.get("rounds", 1)),
        # Count ticks on the circuit being noised. Idle noise is applied at every
        # flattened TICK, so the per-tick share must use the flattened count too.
        num_ticks=count_flattened_ticks(stim_circuit),
        options=options,
    )
    noisy_circuit = noise_builder.noisy_copy(stim_circuit)
    # PAULI_CHANNEL_1 idle noise needs approximate_disjoint_errors: Stim then treats the
    # disjoint X/Y/Z cases as independent, which is accurate for small probabilities.
    detector_model = noisy_circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)

    info = dict(circuit_info)
    info["noise_model"] = "iqm_calibration"
    info["implemented_noise_model"] = "iqm_calibration_per_qubit"
    info["noise_calibration_file"] = str(calibration_file)
    info["calibration_noise"] = noise_builder.metadata()
    info["detector_model_num_errors"] = _count_detector_model_errors(detector_model)

    return noisy_circuit, detector_model, measurement_order, info


# Converting average gate infidelity r (randomized benchmarking) to the probability p
# of a uniformly random non-identity Pauli: r = p * d / (d + 1), with d = 2**n.
RB_TO_PAULI = {"one_qubit": 3.0 / 2.0, "two_qubit": 5.0 / 4.0}
DEFAULT_ROUND_DURATION_S = 1e-6


class _IqmNoiseBuilder:
    """Inject per-qubit / per-coupler calibration noise into a Stim circuit.

    Model (see docs/CALIBRATED_SIMULATION.md):
    - gates: DEPOLARIZE1/2 after H/X/Z and CX/CZ; randomized-benchmarking
      infidelities are converted to Pauli probabilities for IQM observation sets;
    - readout: symmetric flip before M/MX/MR/MRX with the mean assignment error;
    - idle: per round, a Pauli-twirled T1/T2 channel for `round_duration_s`,
      spread evenly over the TICKs of one round;
    - QND: a flip after a measurement only when the qubit is reused without a
      reset (never in reset-based memory circuits);
    - reset: IQM dumps carry no reset error (recorded in metadata).
    """

    def __init__(
        self,
        hardware: dict[str, Any],
        mapping_info: dict[str, Any],
        rounds: int,
        num_ticks: int,
        options: dict[str, Any],
    ) -> None:
        self.hardware = hardware
        self.mapping_info = mapping_info
        self.options = options
        self.stim_to_hardware = {
            int(stim_qubit): hardware_label
            for stim_qubit, hardware_label in mapping_info["stim_to_hardware"].items()
        }
        self.active_stim_qubits = sorted(self.stim_to_hardware)
        self.hardware_graph = _hardware_graph(hardware)
        self.route_cache: dict[tuple[str, str], list[str] | None] = {}
        self.operation_counts = {
            "one_qubit_noise": 0,
            "two_qubit_noise": 0,
            "measurement_noise": 0,
            "qnd_noise": 0,
            "reset_noise": 0,
            "idle_noise": 0,
            "routed_two_qubit_interactions": 0,
        }
        ticks = max(1, int(num_ticks))
        rounds = max(1, rounds)
        self.idle_tick_fraction = float(options.get("idle_tick_fraction", rounds / ticks))
        self.route_error_multiplier = float(options.get("route_error_multiplier", 1.0))
        self.missing_coupler_error = float(options.get("missing_coupler_error", 0.25))
        self.from_iqm_observations = hardware.get("source_schema") == "iqm_observation_set"
        self.rb_to_pauli = bool(options.get("rb_to_pauli", self.from_iqm_observations))
        self.round_duration_s = float(options.get("round_duration_s", DEFAULT_ROUND_DURATION_S))
        # Ramsey T2 applies to idling without dynamical decoupling; use "echo" when DD is on.
        self.idle_t2 = str(options.get("idle_t2", "ramsey"))
        if self.idle_t2 not in {"ramsey", "echo"}:
            raise ValueError("noise.options.idle_t2 must be 'ramsey' or 'echo'")
        default_idle_model = "pauli_twirl" if self.from_iqm_observations else "depolarize"
        self.idle_model = str(options.get("idle_model", default_idle_model))
        self.error_scales = {
            "one_qubit": float(options.get("one_qubit_scale", 1.0)),
            "two_qubit": float(options.get("two_qubit_scale", 1.0)),
            "measurement": float(options.get("measurement_scale", 1.0)),
            "measurement_terminal": float(options.get("measurement_scale", 1.0)),
            "reset": float(options.get("reset_scale", 1.0)),
            "idle": float(options.get("idle_scale", 1.0)),
            "qnd": float(options.get("qnd_scale", 1.0)),
        }

    def noisy_copy(self, stim_circuit: stim.Circuit) -> stim.Circuit:
        instructions = list(stim_circuit.flattened())
        used_later = _qubits_used_later(instructions)
        noisy = stim.Circuit()
        for index, instruction in enumerate(instructions):
            name = instruction.name
            targets = _qubit_targets(instruction)

            if name in {"M", "MR", "MX", "MRX"}:
                basis = "x" if name in {"MX", "MRX"} else "z"
                self._append_noisy_measurement(noisy, name, targets, used_later[index])
                if name in {"MR", "MRX"}:
                    self._append_reset_noise(noisy, targets, basis=basis)
                else:
                    self._append_qnd_noise(noisy, targets, used_later[index], basis=basis)
                continue

            if name == "CX" and _is_classically_controlled(instruction):
                # Feed-forward reset: a feedback-conditioned single-qubit pulse (IQM cc_prx).
                noisy.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
                self._append_one_qubit_noise(noisy, targets)
                continue

            noisy.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())

            if name == "R":
                self._append_reset_noise(noisy, targets, basis="z")
            elif name == "RX":
                self._append_reset_noise(noisy, targets, basis="x")
            elif name in {"H", "X", "Z"}:
                self._append_one_qubit_noise(noisy, targets)
            elif name in {"CX", "CZ"}:
                self._append_two_qubit_noise(noisy, targets)
            elif name == "TICK" and bool(self.options.get("apply_idle", True)):
                self._append_idle_noise(noisy)

        return noisy

    def metadata(self) -> dict[str, Any]:
        return {
            "qpu": self.hardware.get("qpu"),
            "source_schema": self.hardware.get("source_schema"),
            "mapped_qubits": len(self.stim_to_hardware),
            "operation_counts": self.operation_counts,
            "idle_tick_fraction": self.idle_tick_fraction,
            "idle_model": self.idle_model,
            "idle_t2": self.idle_t2,
            "round_duration_s": self.round_duration_s,
            "rb_to_pauli": self.rb_to_pauli,
            "reset_error_available": not self.from_iqm_observations,
            "route_error_multiplier": self.route_error_multiplier,
            "missing_coupler_error": self.missing_coupler_error,
            "error_scales": self.error_scales,
            "one_qubit_error": _stats(self._qubit_error_values("one_qubit")),
            "measurement_error": _stats(self._qubit_error_values("measurement")),
            "measurement_terminal_error": _stats(self._qubit_error_values("measurement_terminal")),
            "qnd_error": _stats(self._qubit_error_values("qnd")),
            "idle_error_per_round": _stats(
                [sum(self._idle_pauli_per_round(stim_qubit)) for stim_qubit in self.active_stim_qubits]
            ),
            "two_qubit_error": _stats(self._mapped_two_qubit_values()),
        }

    def _append_one_qubit_noise(self, circuit: stim.Circuit, stim_qubits: list[int]) -> None:
        for stim_qubit in stim_qubits:
            probability = self._gate_probability(self._qubit_error(stim_qubit, "one_qubit"), "one_qubit")
            if probability:
                circuit.append("DEPOLARIZE1", [stim_qubit], probability)
                self.operation_counts["one_qubit_noise"] += 1

    def _append_two_qubit_noise(self, circuit: stim.Circuit, stim_qubits: list[int]) -> None:
        _require_even_targets("two-qubit noise", stim_qubits)
        for index in range(0, len(stim_qubits), 2):
            left = stim_qubits[index]
            right = stim_qubits[index + 1]
            probability = self._gate_probability(self._two_qubit_error(left, right), "two_qubit")
            if probability:
                circuit.append("DEPOLARIZE2", [left, right], probability)
                self.operation_counts["two_qubit_noise"] += 1

    def _gate_probability(self, infidelity: float, kind: str) -> float:
        if not self.rb_to_pauli:
            return infidelity
        # DEPOLARIZE1 accepts p <= 3/4 and DEPOLARIZE2 accepts p <= 15/16.
        limit = 0.75 if kind == "one_qubit" else 15.0 / 16.0
        return min(infidelity * RB_TO_PAULI[kind], limit)

    def _append_noisy_measurement(
        self,
        circuit: stim.Circuit,
        name: str,
        stim_qubits: list[int],
        used_later: set[int],
    ) -> None:
        """Emit one measurement per qubit with a *classical* readout flip, Stim `M(p)`.

        A classification error flips only the recorded bit, not the qubit. With
        unconditional reset this is equivalent to a flip before the measurement, but
        with feed-forward or no reset the two differ (Gehér et al., arXiv:2408.00758).
        Mid-circuit readouts use the `measure` calibration; final readouts of qubits
        that are not used again use `measure_fidelity` (`measurement_terminal`).
        The converter merges these consecutive per-qubit measurements back into one
        multiplexed readout block.
        """
        for stim_qubit in stim_qubits:
            kind = "measurement" if stim_qubit in used_later else "measurement_terminal"
            probability = self._qubit_error(stim_qubit, kind)
            circuit.append(name, [stim_qubit], [probability] if probability else [])
            if probability:
                self.operation_counts["measurement_noise"] += 1

    def _append_qnd_noise(
        self,
        circuit: stim.Circuit,
        stim_qubits: list[int],
        used_later: set[int],
        basis: str,
    ) -> None:
        """Non-QND flip of the post-measurement state, only if the qubit is reused."""
        gate = "X_ERROR" if basis == "z" else "Z_ERROR"
        for stim_qubit in stim_qubits:
            if stim_qubit not in used_later:
                continue
            probability = self._qubit_error(stim_qubit, "qnd")
            if probability:
                circuit.append(gate, [stim_qubit], probability)
                self.operation_counts["qnd_noise"] += 1

    def _append_reset_noise(
        self,
        circuit: stim.Circuit,
        stim_qubits: list[int],
        basis: str,
    ) -> None:
        gate = "X_ERROR" if basis == "z" else "Z_ERROR"
        for stim_qubit in stim_qubits:
            probability = self._qubit_error(stim_qubit, "reset")
            if probability:
                circuit.append(gate, [stim_qubit], probability)
                self.operation_counts["reset_noise"] += 1

    def _append_idle_noise(self, circuit: stim.Circuit) -> None:
        for stim_qubit in self.active_stim_qubits:
            px, py, pz = (
                _clamp_probability(self.idle_tick_fraction * value)
                for value in self._idle_pauli_per_round(stim_qubit)
            )
            if not (px or py or pz):
                continue
            if self.idle_model == "pauli_twirl":
                circuit.append("PAULI_CHANNEL_1", [stim_qubit], [px, py, pz])
            else:
                circuit.append("DEPOLARIZE1", [stim_qubit], px + py + pz)
            self.operation_counts["idle_noise"] += 1

    def _idle_pauli_per_round(self, stim_qubit: int) -> tuple[float, float, float]:
        """(px, py, pz) for one round of idling, already scaled by idle_scale."""
        label = self.stim_to_hardware.get(stim_qubit)
        if label is None:
            return 0.0, 0.0, 0.0
        scale = self.error_scales["idle"]
        if self.idle_model == "pauli_twirl":
            times = self.hardware["qubits"][label].get("calibration", {}) or {}
            t1 = times.get("t1_time")
            if self.idle_t2 == "echo":
                t2 = times.get("t2_echo_time") or times.get("t2_time")
            else:
                t2 = times.get("t2_time") or times.get("t2_echo_time")
            if t1 and t2:
                px, py, pz = _pauli_twirl_idle(self.round_duration_s, t1, t2)
                return scale * px, scale * py, scale * pz
        # Fallback: depolarizing idle with the per-round idle error from the calibration.
        probability = self._qubit_error(stim_qubit, "idle")
        return probability / 3.0, probability / 3.0, probability / 3.0

    def _qubit_error(self, stim_qubit: int, name: str) -> float:
        label = self.stim_to_hardware.get(stim_qubit)
        if label is None:
            return 0.0
        errors = self.hardware["qubits"][label]["errors"]
        scale = self.error_scales.get(name, 1.0)
        if name == "measurement_terminal" and name not in errors:
            name = "measurement"  # calibrations without a separate terminal readout
        return _clamp_probability(scale * float(errors.get(name, 0.0)))

    def _two_qubit_error(self, left_stim: int, right_stim: int) -> float:
        left = self.stim_to_hardware[left_stim]
        right = self.stim_to_hardware[right_stim]
        pair = _sorted_pair(left, right)
        scale = self.error_scales["two_qubit"]
        if pair in self.hardware["couplers"]:
            return _clamp_probability(scale * float(self.hardware["couplers"][pair]))

        path = self._route(left, right)
        if not path:
            self.operation_counts["routed_two_qubit_interactions"] += 1
            return _clamp_probability(scale * self.missing_coupler_error)

        self.operation_counts["routed_two_qubit_interactions"] += 1
        path_errors = []
        for index in range(len(path) - 1):
            edge = _sorted_pair(path[index], path[index + 1])
            path_errors.append(float(self.hardware["couplers"].get(edge, self.missing_coupler_error)))
        return _clamp_probability(scale * self.route_error_multiplier * _combined_probability(path_errors))

    def _route(self, left: str, right: str) -> list[str] | None:
        pair = _sorted_pair(left, right)
        if pair not in self.route_cache:
            try:
                self.route_cache[pair] = nx.shortest_path(self.hardware_graph, left, right)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                self.route_cache[pair] = None
        return self.route_cache[pair]

    def _qubit_error_values(self, name: str) -> list[float]:
        return [self._qubit_error(stim_qubit, name) for stim_qubit in self.active_stim_qubits]

    def _mapped_two_qubit_values(self) -> list[float]:
        values = []
        for pair in self.hardware["couplers"]:
            if pair[0] in self.stim_to_hardware.values() and pair[1] in self.stim_to_hardware.values():
                values.append(float(self.hardware["couplers"][pair]))
        return values


def _pauli_twirl_idle(duration: float, t1: float, t2: float) -> tuple[float, float, float]:
    """Pauli-twirled amplitude and phase damping for an idle of `duration` seconds."""
    decay_1 = 1.0 - np.exp(-duration / t1)
    decay_2 = 1.0 - np.exp(-duration / t2)
    px = py = decay_1 / 4.0
    pz = max(0.0, decay_2 / 2.0 - decay_1 / 4.0)
    return float(px), float(py), float(pz)


def _is_classically_controlled(instruction: stim.CircuitInstruction) -> bool:
    return any(target.is_measurement_record_target for target in instruction.targets_copy())


def _qubits_used_later(instructions: list[stim.CircuitInstruction]) -> list[set[int]]:
    """For each instruction, the qubits touched by any later gate, reset, or measurement."""
    ignored = {"TICK", "DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"}
    used_later: list[set[int]] = [set() for _ in instructions]
    seen: set[int] = set()
    for index in range(len(instructions) - 1, -1, -1):
        used_later[index] = set(seen)
        if instructions[index].name not in ignored:
            seen.update(_qubit_targets(instructions[index]))
    return used_later


def _hardware_graph(hardware: dict[str, Any]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(hardware["qubits"])
    graph.add_edges_from(hardware["couplers"])
    return graph


def _qubit_targets(instruction: stim.CircuitInstruction) -> list[int]:
    return [
        target.value
        for target in instruction.targets_copy()
        if target.is_qubit_target
    ]


def _require_even_targets(name: str, targets: list[int]) -> None:
    if len(targets) % 2 != 0:
        raise ValueError(f"{name} requires an even number of qubit targets")


def _sorted_pair(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right), key=_label_sort_key))


def _label_sort_key(label: str) -> tuple[int, int | str]:
    if label.upper().startswith("QB") and label[2:].isdigit():
        return (0, int(label[2:]))
    return (1, label)


def _combined_probability(probabilities: list[float]) -> float:
    keep_probability = 1.0
    for probability in probabilities:
        keep_probability *= 1.0 - _clamp_probability(probability)
    return _clamp_probability(1.0 - keep_probability)


def _clamp_probability(probability: float) -> float:
    return min(max(float(probability), 0.0), 1.0)


def _stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def _count_detector_model_errors(detector_model: stim.DetectorErrorModel) -> int:
    return sum(
        1
        for instruction in detector_model
        if instruction.type == "error"
    )
