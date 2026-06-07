from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import stim
import yaml

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
        num_ticks=int(circuit_info.get("num_ticks", 1)),
        options=options,
    )
    noisy_circuit = noise_builder.noisy_copy(stim_circuit)
    detector_model = noisy_circuit.detector_error_model(decompose_errors=True)

    info = dict(circuit_info)
    info["noise_model"] = "iqm_calibration"
    info["implemented_noise_model"] = "iqm_calibration_per_qubit"
    info["noise_calibration_file"] = str(calibration_file)
    info["calibration_noise"] = noise_builder.metadata()
    info["detector_model_num_errors"] = _count_detector_model_errors(detector_model)

    return noisy_circuit, detector_model, measurement_order, info


class _IqmNoiseBuilder:
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
            "reset_noise": 0,
            "idle_noise": 0,
            "routed_two_qubit_interactions": 0,
        }
        ticks = max(1, int(num_ticks))
        rounds = max(1, rounds)
        self.idle_tick_fraction = float(options.get("idle_tick_fraction", rounds / ticks))
        self.route_error_multiplier = float(options.get("route_error_multiplier", 1.0))
        self.missing_coupler_error = float(options.get("missing_coupler_error", 0.25))
        self.error_scales = {
            "one_qubit": float(options.get("one_qubit_scale", 1.0)),
            "two_qubit": float(options.get("two_qubit_scale", 1.0)),
            "measurement": float(options.get("measurement_scale", 1.0)),
            "reset": float(options.get("reset_scale", 1.0)),
            "idle": float(options.get("idle_scale", 1.0)),
            "qnd": float(options.get("qnd_scale", 1.0)),
        }

    def noisy_copy(self, stim_circuit: stim.Circuit) -> stim.Circuit:
        noisy = stim.Circuit()
        for instruction in stim_circuit.flattened():
            name = instruction.name
            targets = _qubit_targets(instruction)

            if name in {"M", "MR"}:
                self._append_measurement_noise(noisy, targets, basis="z")
                noisy.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
                if name == "MR":
                    self._append_reset_noise(noisy, targets, basis="z")
                continue

            if name in {"MX", "MRX"}:
                self._append_measurement_noise(noisy, targets, basis="x")
                noisy.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
                if name == "MRX":
                    self._append_reset_noise(noisy, targets, basis="x")
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
            "route_error_multiplier": self.route_error_multiplier,
            "missing_coupler_error": self.missing_coupler_error,
            "error_scales": self.error_scales,
            "one_qubit_error": _stats(self._qubit_error_values("one_qubit")),
            "measurement_error": _stats(self._qubit_error_values("measurement")),
            "qnd_error": _stats(self._qubit_error_values("qnd")),
            "idle_error_per_round": _stats(self._qubit_error_values("idle")),
            "two_qubit_error": _stats(self._mapped_two_qubit_values()),
        }

    def _append_one_qubit_noise(self, circuit: stim.Circuit, stim_qubits: list[int]) -> None:
        for stim_qubit in stim_qubits:
            probability = self._qubit_error(stim_qubit, "one_qubit")
            if probability:
                circuit.append("DEPOLARIZE1", [stim_qubit], probability)
                self.operation_counts["one_qubit_noise"] += 1

    def _append_two_qubit_noise(self, circuit: stim.Circuit, stim_qubits: list[int]) -> None:
        _require_even_targets("two-qubit noise", stim_qubits)
        for index in range(0, len(stim_qubits), 2):
            left = stim_qubits[index]
            right = stim_qubits[index + 1]
            probability = self._two_qubit_error(left, right)
            if probability:
                circuit.append("DEPOLARIZE2", [left, right], probability)
                self.operation_counts["two_qubit_noise"] += 1

    def _append_measurement_noise(
        self,
        circuit: stim.Circuit,
        stim_qubits: list[int],
        basis: str,
    ) -> None:
        gate = "X_ERROR" if basis == "z" else "Z_ERROR"
        for stim_qubit in stim_qubits:
            measurement = self._qubit_error(stim_qubit, "measurement")
            qnd = self._qubit_error(stim_qubit, "qnd")
            probability = _combined_probability([measurement, qnd])
            if probability:
                circuit.append(gate, [stim_qubit], probability)
                self.operation_counts["measurement_noise"] += 1

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
            probability = self.idle_tick_fraction * self._qubit_error(stim_qubit, "idle")
            probability = _clamp_probability(probability)
            if probability:
                circuit.append("DEPOLARIZE1", [stim_qubit], probability)
                self.operation_counts["idle_noise"] += 1

    def _qubit_error(self, stim_qubit: int, name: str) -> float:
        label = self.stim_to_hardware.get(stim_qubit)
        if label is None:
            return 0.0
        errors = self.hardware["qubits"][label]["errors"]
        scale = self.error_scales.get(name, 1.0)
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
