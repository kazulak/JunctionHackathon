"""IQM calibration data: loading, parsing to a per-qubit/per-coupler table, and qubit labels."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import yaml

IQM_QUBIT_RE = re.compile(r"QB\d+")
DEFAULT_ROUND_SECONDS = 1e-6


def load_calibration(path: str | Path) -> dict[str, Any]:
    """Read a calibration file: an IQM observation set (.json) or a hand-written grid (.yaml)."""
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def parse_hardware_calibration(
    calibration: dict[str, Any],
    exclude_qubits: list[str] | None = None,
) -> dict[str, Any]:
    """Parse supported calibration formats into the internal hardware table."""
    hardware = parse_hardware(calibration)
    return filter_hardware_qubits(hardware, exclude_qubits or [])


def parse_hardware(calibration: dict[str, Any]) -> dict[str, Any]:
    if "observations" in calibration:
        return _parse_iqm_observation_set(calibration)

    qubits = {}
    coord_to_label = {}
    for label, data in calibration.get("qubits", {}).items():
        if data.get("disabled", False):
            continue
        row = int(data["row"])
        col = int(data["col"])
        qubits[label] = {
            "label": label,
            "row": row,
            "col": col,
            "index": int(data.get("index", index_from_label(label))),
            "errors": data.get("errors", {}),
        }
        coord_to_label[(row, col)] = label

    couplers = {}
    for item in calibration.get("couplers", []):
        if item.get("disabled", False):
            continue
        labels = sorted_pair(item["qubits"][0], item["qubits"][1])
        couplers[labels] = float(item.get("error", 0.0))

    return {
        "qpu": calibration.get("qpu"),
        "qubits": qubits,
        "coord_to_label": coord_to_label,
        "couplers": couplers,
        "has_couplers": bool(couplers),
        "source_schema": "patch_grid",
    }


def _parse_iqm_observation_set(calibration: dict[str, Any]) -> dict[str, Any]:
    qubit_labels = set()
    one_qubit_errors: dict[str, list[float]] = {}
    # Mid-circuit readout ("measure") and the high-fidelity terminal readout
    # ("measure_fidelity", e.g. shelved) are calibrated separately on IQM QPUs.
    assignment_errors: dict[str, list[float]] = {}
    readout_infidelities: dict[str, list[float]] = {}
    terminal_assignment_errors: dict[str, list[float]] = {}
    terminal_readout_infidelities: dict[str, list[float]] = {}
    qnd_values: dict[str, list[float]] = {}
    t1_times: dict[str, float] = {}
    t2_times: dict[str, float] = {}
    t2_echo_times: dict[str, float] = {}
    coupler_candidates: dict[tuple[str, str], list[tuple[int, float]]] = {}

    for observation in calibration.get("observations", []):
        field = str(observation.get("dut_field", ""))
        value = float(observation.get("value", 0.0))
        labels = IQM_QUBIT_RE.findall(field)
        qubit_labels.update(labels)

        if len(labels) == 1:
            label = labels[0]
            terminal = ".ssro.measure_fidelity." in field
            if "ssro.measure" in field and field.endswith(("error_0_to_1", "error_1_to_0")):
                target = terminal_assignment_errors if terminal else assignment_errors
                target.setdefault(label, []).append(value)
            elif "ssro.measure" in field and field.endswith(".fidelity"):
                target = terminal_readout_infidelities if terminal else readout_infidelities
                target.setdefault(label, []).append(1.0 - value)
            elif ".rb.prx." in field and ".fidelity" in field:
                one_qubit_errors.setdefault(label, []).append(1.0 - value)
            elif ".rb.clifford." in field and ".fidelity" in field:
                one_qubit_errors.setdefault(label, []).append(1.0 - value)
            elif "qndness" in field and field.endswith(("qndness_0", "qndness_1")):
                qnd_values.setdefault(label, []).append(value)
            elif field.endswith(".t1_time"):
                t1_times[label] = value
            elif field.endswith(".t2_time"):
                t2_times[label] = value
            elif field.endswith(".t2_echo_time"):
                t2_echo_times[label] = value

        if len(labels) >= 2 and field.endswith("fidelity:par=d2"):
            pair = tuple(sorted(labels[:2], key=index_from_label))
            priority = 0 if ".irb.cz." in field else 1
            coupler_candidates.setdefault(pair, []).append((priority, 1.0 - value))

    qubits = {}
    for label in sorted(qubit_labels, key=index_from_label):
        qnd_error = 1.0 - min(qnd_values[label]) if label in qnd_values else 0.0
        idle_time = t2_echo_times.get(label) or t2_times.get(label)
        idle_error = 1.0 - np.exp(-DEFAULT_ROUND_SECONDS / idle_time) if idle_time else 0.0
        qubits[label] = {
            "label": label,
            "index": index_from_label(label),
            "errors": {
                "one_qubit": min(one_qubit_errors.get(label, [0.0])),
                "measurement": _readout_error(
                    assignment_errors.get(label, []),
                    readout_infidelities.get(label, []),
                ),
                "measurement_terminal": _readout_error(
                    terminal_assignment_errors.get(label, []) or assignment_errors.get(label, []),
                    terminal_readout_infidelities.get(label, []) or readout_infidelities.get(label, []),
                ),
                "reset": 0.0,
                "idle": idle_error,
                "qnd": qnd_error,
            },
            "calibration": {
                "t1_time": t1_times.get(label),
                "t2_time": t2_times.get(label),
                "t2_echo_time": t2_echo_times.get(label),
            },
        }

    couplers = {}
    for pair, candidates in coupler_candidates.items():
        best_priority = min(priority for priority, _error in candidates)
        best_errors = [
            error
            for priority, error in candidates
            if priority == best_priority
        ]
        couplers[pair] = min(best_errors)

    return {
        "qpu": calibration.get("dut_label") or calibration.get("describes_id"),
        "qubits": qubits,
        "coord_to_label": {},
        "couplers": couplers,
        "has_couplers": bool(couplers),
        "source_schema": "iqm_observation_set",
    }


def _readout_error(assignment_errors: list[float], infidelities: list[float]) -> float:
    """Symmetric readout flip probability for a qubit.

    The mean of the 0->1 and 1->0 assignment errors is the error averaged over
    the two prepared states. Stim's pre-measurement flip is symmetric, so this
    is the closest single number (the old code took the maximum of all fields,
    which overstated readout error for the 0 state).
    """
    if assignment_errors:
        return float(np.mean(assignment_errors))
    if infidelities:
        return float(np.mean(infidelities))
    return 0.0


def filter_hardware_qubits(hardware: dict[str, Any], exclude_qubits: list[str]) -> dict[str, Any]:
    excluded = {normalize_qubit_label(label) for label in exclude_qubits}
    if not excluded:
        return hardware

    qubits = {
        label: data
        for label, data in hardware["qubits"].items()
        if label not in excluded
    }
    couplers = {
        pair: error
        for pair, error in hardware["couplers"].items()
        if pair[0] in qubits and pair[1] in qubits
    }
    coord_to_label = {
        coord: label
        for coord, label in hardware["coord_to_label"].items()
        if label in qubits
    }
    result = dict(hardware)
    result["qubits"] = qubits
    result["couplers"] = couplers
    result["coord_to_label"] = coord_to_label
    result["has_couplers"] = bool(couplers)
    result["excluded_qubits"] = sorted(excluded, key=label_sort_key)
    return result


def build_hardware_graph(hardware: dict[str, Any]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(hardware["qubits"])
    graph.add_edges_from(hardware["couplers"])
    return graph


def index_from_label(label: str) -> int:
    if label.upper().startswith("QB"):
        return int(label[2:]) - 1
    raise ValueError(f"Qubit label {label!r} needs explicit qiskit index")


def label_sort_key(label: str) -> tuple[int, int | str]:
    if label.upper().startswith("QB") and label[2:].isdigit():
        return (0, int(label[2:]))
    return (1, label)


def sorted_pair(left: str, right: str) -> tuple[str, str]:
    first, second = sorted((left, right), key=label_sort_key)
    return (first, second)


def normalize_qubit_label(label: str | int) -> str:
    if isinstance(label, int):
        return f"QB{label}"
    text = str(label).strip().upper()
    if text.startswith("QB"):
        return f"QB{int(text[2:])}"
    if text.isdigit():
        return f"QB{int(text)}"
    raise ValueError(f"Invalid qubit label in exclude_qubits: {label!r}")
