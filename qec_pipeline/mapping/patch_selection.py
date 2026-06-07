from __future__ import annotations

from collections import Counter
from pathlib import Path
import random
import re
from typing import Any

import networkx as nx
import numpy as np
from scipy.optimize import linear_sum_assignment
import stim
import yaml


IQM_QUBIT_RE = re.compile(r"QB\d+")
DEFAULT_ROUND_SECONDS = 1e-6


def select_calibration_best_patch(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
    calibration: dict[str, Any],
    weights: dict[str, float] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the lowest-score hardware patch for a Stim surface-code circuit."""
    weights = weights or {}
    options = options or {}
    interaction_counts = two_qubit_interaction_counts(stim_circuit)
    roles = surface_code_qubit_roles(stim_circuit, stim_to_dense)
    hardware = _parse_hardware(calibration)
    hardware = _filter_hardware_qubits(hardware, options.get("exclude_qubits", []) or [])

    if not hardware["coord_to_label"]:
        best = _select_graph_patch(stim_to_dense, interaction_counts, roles, hardware, weights)
        best["strategy"] = "calibration_best_patch"
        best["excluded_qubits"] = hardware.get("excluded_qubits", [])
        return best

    patch_coords = surface_code_patch_coordinates(stim_circuit, stim_to_dense)
    candidates = []
    max_patch_row = max(row for row, _col in patch_coords.values())
    max_patch_col = max(col for _row, col in patch_coords.values())

    hardware_rows = [row for row, _col in hardware["coord_to_label"]]
    hardware_cols = [col for _row, col in hardware["coord_to_label"]]
    for origin_row in range(min(hardware_rows), max(hardware_rows) - max_patch_row + 1):
        for origin_col in range(min(hardware_cols), max(hardware_cols) - max_patch_col + 1):
            candidate = _score_candidate(
                origin=(origin_row, origin_col),
                patch_coords=patch_coords,
                stim_to_dense=stim_to_dense,
                interaction_counts=interaction_counts,
                roles=roles,
                hardware=hardware,
                weights=weights,
            )
            if candidate is not None:
                candidates.append(candidate)

    if not candidates:
        raise ValueError("No valid hardware patch found for this circuit and calibration data")

    best = min(candidates, key=lambda item: item["score"])
    best["num_candidates"] = len(candidates)
    best["strategy"] = "calibration_best_patch"
    best["excluded_qubits"] = hardware.get("excluded_qubits", [])
    return best


def select_calibration_routed_layout(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
    calibration: dict[str, Any],
    weights: dict[str, float] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a low-cost initial layout when the exact native patch does not exist."""
    weights = weights or {}
    options = options or {}
    interaction_counts = two_qubit_interaction_counts(stim_circuit)
    roles = surface_code_qubit_roles(stim_circuit, stim_to_dense)
    hardware = _parse_hardware(calibration)
    hardware = _filter_hardware_qubits(hardware, options.get("exclude_qubits", []) or [])
    hardware_graph = _hardware_graph(hardware)
    patch_coords = surface_code_patch_coordinates(stim_circuit, stim_to_dense)

    if len(hardware["qubits"]) < len(stim_to_dense):
        raise ValueError(
            "Not enough hardware qubits after mapping.options.exclude_qubits: "
            f"{len(hardware['qubits'])} < {len(stim_to_dense)}"
        )

    initial_assignments = _initial_routed_assignments(
        patch_coords=patch_coords,
        hardware=hardware,
        hardware_graph=hardware_graph,
        roles=roles,
        weights=weights,
    )
    score_assignment = _routed_score_function(
        stim_to_dense=stim_to_dense,
        interaction_counts=interaction_counts,
        roles=roles,
        hardware=hardware,
        hardware_graph=hardware_graph,
        weights=weights,
    )

    best = None
    best_metadata = {}
    seed = int(options.get("seed", 1))
    max_iterations = int(options.get("max_iterations", 5000))
    hardware_labels = list(hardware["qubits"])

    for offset, assignment in enumerate(initial_assignments):
        improved, metadata = _improve_routed_assignment(
            assignment=assignment,
            hardware_labels=hardware_labels,
            score_assignment=score_assignment,
            seed=seed + offset,
            max_iterations=max_iterations,
        )
        score, routed_metadata = score_assignment(improved)
        if best is None or score < best["score"]:
            best = _assignment_to_mapping(improved, stim_to_dense, roles, hardware, score)
            best_metadata = metadata | routed_metadata

    if best is None:
        raise ValueError("No routed hardware layout found for this circuit and calibration data")

    best["strategy"] = "calibration_routed_layout"
    best["selection"] = "routed_graph"
    best["source_schema"] = hardware["source_schema"]
    best["num_candidates"] = len(initial_assignments)
    best["routing"] = best_metadata
    best["excluded_qubits"] = hardware.get("excluded_qubits", [])
    return best


def select_mapping_from_config(
    mapping: dict[str, Any],
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
) -> dict[str, Any] | None:
    """Return mapping metadata for the configured strategy."""
    strategy = mapping.get("strategy", "none")
    if strategy in {"none", None}:
        return None

    hardware_patch = mapping.get("hardware_patch")
    if hardware_patch and hardware_patch.get("stim_to_hardware"):
        calibration_file = mapping.get("calibration_file")
        if not calibration_file:
            raise ValueError("mapping.calibration_file is required for fixed hardware_patch")
        calibration = yaml.safe_load(Path(calibration_file).read_text(encoding="utf-8")) or {}
        return select_fixed_stim_to_hardware_patch(
            stim_circuit,
            stim_to_dense,
            calibration,
            hardware_patch["stim_to_hardware"],
            weights=mapping.get("weights"),
            options=mapping.get("options"),
        )

    calibration_file = mapping.get("calibration_file")
    if not calibration_file:
        raise ValueError(f"mapping.calibration_file is required for {strategy}")
    calibration = yaml.safe_load(Path(calibration_file).read_text(encoding="utf-8")) or {}
    if strategy == "calibration_best_patch":
        return select_calibration_best_patch(
            stim_circuit,
            stim_to_dense,
            calibration,
            weights=mapping.get("weights"),
            options=mapping.get("options"),
        )
    if strategy == "calibration_routed_layout":
        return select_calibration_routed_layout(
            stim_circuit,
            stim_to_dense,
            calibration,
            weights=mapping.get("weights"),
            options=mapping.get("options"),
        )
    raise NotImplementedError(f"mapping strategy not implemented: {strategy}")


def active_stim_to_dense(stim_circuit: stim.Circuit) -> dict[int, int]:
    """Return the dense Qiskit order used by the converter and mapper."""
    active = sorted(
        {
            target.value
            for instruction in stim_circuit.flattened()
            for target in instruction.targets_copy()
            if target.is_qubit_target
        }
    )
    return {stim_qubit: index for index, stim_qubit in enumerate(active)}


def parse_hardware_calibration(
    calibration: dict[str, Any],
    exclude_qubits: list[str] | None = None,
) -> dict[str, Any]:
    """Parse supported calibration formats into the internal hardware table."""
    hardware = _parse_hardware(calibration)
    return _filter_hardware_qubits(hardware, exclude_qubits or [])


def select_fixed_stim_to_hardware_patch(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
    calibration: dict[str, Any],
    stim_to_hardware: dict[str, str] | dict[int, str],
    weights: dict[str, float] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Use a pinned Stim-qubit-to-hardware-qubit assignment from YAML."""
    weights = weights or {}
    options = options or {}
    interaction_counts = two_qubit_interaction_counts(stim_circuit)
    roles = surface_code_qubit_roles(stim_circuit, stim_to_dense)
    hardware = _parse_hardware(calibration)
    hardware = _filter_hardware_qubits(hardware, options.get("exclude_qubits", []) or [])

    normalized = {int(stim): _normalize_qubit_label(label) for stim, label in stim_to_hardware.items()}
    missing = sorted(set(stim_to_dense) - set(normalized))
    extra = sorted(set(normalized) - set(stim_to_dense))
    if missing or extra:
        raise ValueError(
            "fixed hardware_patch.stim_to_hardware does not match active Stim qubits: "
            f"missing={missing}, extra={extra}"
        )

    unknown = sorted({label for label in normalized.values() if label not in hardware["qubits"]})
    if unknown:
        raise ValueError(f"fixed hardware patch uses unavailable hardware qubits: {unknown}")

    selected = _score_assignment(
        normalized,
        stim_to_dense,
        interaction_counts,
        roles,
        hardware,
        weights,
    )
    if selected is None:
        raise ValueError("fixed hardware patch is missing required native couplers")

    selected["strategy"] = "fixed_stim_to_hardware"
    selected["selection"] = "fixed_stim_to_hardware"
    selected["source_schema"] = hardware["source_schema"]
    selected["num_candidates"] = 1
    selected["excluded_qubits"] = hardware.get("excluded_qubits", [])
    return selected


def surface_code_patch_coordinates(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
) -> dict[int, tuple[int, int]]:
    """Map Stim rotated surface-code coordinates onto compact hardware-patch coordinates."""
    coords = stim_circuit.get_final_qubit_coordinates()
    patch_raw = {}
    for stim_qubit in stim_to_dense:
        x, y = coords[stim_qubit]
        patch_raw[stim_qubit] = (round((y - x) / 2), round((x + y) / 2))

    min_row = min(row for row, _col in patch_raw.values())
    min_col = min(col for _row, col in patch_raw.values())
    return {
        stim_qubit: (row - min_row, col - min_col)
        for stim_qubit, (row, col) in patch_raw.items()
    }


def two_qubit_interaction_counts(stim_circuit: stim.Circuit) -> Counter[tuple[int, int]]:
    """Count two-qubit interactions by Stim qubit pair."""
    counts: Counter[tuple[int, int]] = Counter()
    for instruction in stim_circuit.flattened():
        if instruction.name not in {"CX", "CZ"}:
            continue
        targets = [target.value for target in instruction.targets_copy() if target.is_qubit_target]
        for index in range(0, len(targets), 2):
            pair = tuple(sorted((targets[index], targets[index + 1])))
            counts[pair] += 1
    return counts


def surface_code_qubit_roles(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
) -> dict[int, str]:
    """Return `ancilla` for repeated syndrome-measurement qubits, else `data`."""
    ancillas = set()
    for instruction in stim_circuit.flattened():
        if instruction.name in {"MR", "MRX", "MRZ"}:
            ancillas.update(
                target.value
                for target in instruction.targets_copy()
                if target.is_qubit_target
            )

    return {
        stim_qubit: "ancilla" if stim_qubit in ancillas else "data"
        for stim_qubit in stim_to_dense
    }


def _parse_hardware(calibration: dict[str, Any]) -> dict[str, Any]:
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
            "index": int(data.get("index", _index_from_label(label))),
            "errors": data.get("errors", {}),
        }
        coord_to_label[(row, col)] = label

    couplers = {}
    for item in calibration.get("couplers", []):
        if item.get("disabled", False):
            continue
        labels = _sorted_pair(item["qubits"][0], item["qubits"][1])
        couplers[labels] = float(item.get("error", 0.0))

    return {
        "qpu": calibration.get("qpu"),
        "qubits": qubits,
        "coord_to_label": coord_to_label,
        "couplers": couplers,
        "has_couplers": bool(couplers),
        "source_schema": "patch_grid",
    }


def _score_candidate(
    origin: tuple[int, int],
    patch_coords: dict[int, tuple[int, int]],
    stim_to_dense: dict[int, int],
    interaction_counts: Counter[tuple[int, int]],
    roles: dict[int, str],
    hardware: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, Any] | None:
    origin_row, origin_col = origin
    stim_to_hardware = {}
    for stim_qubit, (patch_row, patch_col) in patch_coords.items():
        label = hardware["coord_to_label"].get((origin_row + patch_row, origin_col + patch_col))
        if label is None:
            return None
        stim_to_hardware[stim_qubit] = label

    candidate = _score_assignment(stim_to_hardware, stim_to_dense, interaction_counts, roles, hardware, weights)
    if candidate is None:
        return None
    candidate["origin"] = {"row": origin_row, "col": origin_col}
    return candidate


def _select_graph_patch(
    stim_to_dense: dict[int, int],
    interaction_counts: Counter[tuple[int, int]],
    roles: dict[int, str],
    hardware: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, Any]:
    """Find a native hardware subgraph matching the generated surface-code interactions."""
    code_graph = nx.Graph()
    code_graph.add_nodes_from(stim_to_dense)
    code_graph.add_edges_from(interaction_counts)

    hardware_graph = _hardware_graph(hardware)

    matcher = nx.algorithms.isomorphism.GraphMatcher(hardware_graph, code_graph)
    best = None
    num_candidates = 0

    for hardware_to_stim in matcher.subgraph_monomorphisms_iter():
        stim_to_hardware = {
            stim_qubit: hardware_label
            for hardware_label, stim_qubit in hardware_to_stim.items()
        }
        candidate = _score_assignment(
            stim_to_hardware,
            stim_to_dense,
            interaction_counts,
            roles,
            hardware,
            weights,
        )
        if candidate is None:
            continue
        num_candidates += 1
        if best is None or candidate["score"] < best["score"]:
            best = candidate

    if best is None:
        raise ValueError(
            "No native hardware graph patch found for this circuit and calibration data. "
            "Use a smaller distance or disable mapping so Qiskit can route the circuit."
        )

    best["num_candidates"] = num_candidates
    best["selection"] = "native_graph"
    best["source_schema"] = hardware["source_schema"]
    return best


def _hardware_graph(hardware: dict[str, Any]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(hardware["qubits"])
    graph.add_edges_from(hardware["couplers"])
    return graph


def _filter_hardware_qubits(hardware: dict[str, Any], exclude_qubits: list[str]) -> dict[str, Any]:
    excluded = {_normalize_qubit_label(label) for label in exclude_qubits}
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
    result["excluded_qubits"] = sorted(excluded, key=_label_sort_key)
    return result


def _score_assignment(
    stim_to_hardware: dict[int, str],
    stim_to_dense: dict[int, int],
    interaction_counts: Counter[tuple[int, int]],
    roles: dict[int, str],
    hardware: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, Any] | None:
    score = 0.0
    for stim_qubit, label in stim_to_hardware.items():
        score += _node_error(hardware, label, roles[stim_qubit], weights)

    missing_couplers = []
    max_coupler_error = 0.0
    for (stim_a, stim_b), count in interaction_counts.items():
        labels = _sorted_pair(stim_to_hardware[stim_a], stim_to_hardware[stim_b])
        if hardware["has_couplers"] and labels not in hardware["couplers"]:
            missing_couplers.append(labels)
            continue
        coupler_error = hardware["couplers"].get(labels, 0.0)
        max_coupler_error = max(max_coupler_error, coupler_error)
        score += float(weights.get("two_qubit", 1.0)) * count * coupler_error
    score += float(weights.get("max_coupler", 0.0)) * max_coupler_error

    if missing_couplers:
        return None

    dense_to_hardware = {
        dense: stim_to_hardware[stim_qubit]
        for stim_qubit, dense in stim_to_dense.items()
    }
    initial_layout = [
        hardware["qubits"][dense_to_hardware[dense]]["index"]
        for dense in range(len(dense_to_hardware))
    ]

    return {
        "qpu": hardware["qpu"],
        "score": score,
        "initial_layout": initial_layout,
        "stim_to_hardware": {str(key): value for key, value in sorted(stim_to_hardware.items())},
        "dense_to_hardware": {str(key): value for key, value in sorted(dense_to_hardware.items())},
        "data_hardware": sorted(
            (label for stim_qubit, label in stim_to_hardware.items() if roles[stim_qubit] == "data"),
            key=_label_sort_key,
        ),
        "ancilla_hardware": sorted(
            (label for stim_qubit, label in stim_to_hardware.items() if roles[stim_qubit] == "ancilla"),
            key=_label_sort_key,
        ),
    }


def _initial_routed_assignments(
    patch_coords: dict[int, tuple[int, int]],
    hardware: dict[str, Any],
    hardware_graph: nx.Graph,
    roles: dict[int, str],
    weights: dict[str, float],
) -> list[dict[int, str]]:
    code_nodes = _code_nodes_by_position(patch_coords)
    code_points = _normalized_points({node: patch_coords[node] for node in code_nodes})
    hardware_points = nx.kamada_kawai_layout(hardware_graph, weight=None)
    hardware_labels = list(hardware["qubits"])

    assignments = []
    for transformed in _coordinate_transforms(code_points):
        cost = np.zeros((len(code_nodes), len(hardware_labels)))
        for row, code_node in enumerate(code_nodes):
            code_point = transformed[code_node]
            for col, hardware_label in enumerate(hardware_labels):
                hardware_point = hardware_points[hardware_label]
                distance = np.linalg.norm(code_point - hardware_point)
                cost[row, col] = distance + _node_error(hardware, hardware_label, roles[code_node], weights)

        rows, cols = linear_sum_assignment(cost)
        assignment = {
            code_nodes[row]: hardware_labels[col]
            for row, col in zip(rows, cols)
        }
        assignments.append(assignment)

    label_sorted = sorted(hardware_labels, key=_label_sort_key)
    best_49 = sorted(
        hardware_labels,
        key=lambda label: (_node_error(hardware, label, "ancilla", weights), _label_sort_key(label)),
    )[: len(code_nodes)]
    assignments.append(dict(zip(code_nodes, label_sorted[: len(code_nodes)])))
    assignments.append(dict(zip(code_nodes, sorted(best_49, key=_label_sort_key))))

    unique = []
    seen = set()
    for assignment in assignments:
        signature = tuple(assignment[node] for node in code_nodes)
        if signature not in seen:
            unique.append(assignment)
            seen.add(signature)
    return unique


def _improve_routed_assignment(
    assignment: dict[int, str],
    hardware_labels: list[str],
    score_assignment,
    seed: int,
    max_iterations: int,
) -> tuple[dict[int, str], dict[str, Any]]:
    rng = random.Random(seed)
    current = dict(assignment)
    current_score, _metadata = score_assignment(current)
    best = dict(current)
    best_score = current_score
    code_nodes = list(current)

    for _step in range(max_iterations):
        candidate = dict(current)
        if rng.random() < 0.35:
            used = set(candidate.values())
            unused = [label for label in hardware_labels if label not in used]
            if not unused:
                continue
            code_node = rng.choice(code_nodes)
            candidate[code_node] = rng.choice(unused)
        else:
            left, right = rng.sample(code_nodes, 2)
            candidate[left], candidate[right] = candidate[right], candidate[left]

        candidate_score, _candidate_metadata = score_assignment(candidate)
        if candidate_score < current_score:
            current = candidate
            current_score = candidate_score
            if candidate_score < best_score:
                best = dict(candidate)
                best_score = candidate_score

    return best, {
        "local_search_iterations": max_iterations,
        "local_search_seed": seed,
    }


def _routed_score_function(
    stim_to_dense: dict[int, int],
    interaction_counts: Counter[tuple[int, int]],
    roles: dict[int, str],
    hardware: dict[str, Any],
    hardware_graph: nx.Graph,
    weights: dict[str, float],
):
    shortest_paths = dict(nx.all_pairs_shortest_path(hardware_graph))
    route_distance_weight = float(weights.get("route_distance", 0.2))
    disconnected_penalty = float(weights.get("disconnected", 1000.0))

    def score_assignment(stim_to_hardware: dict[int, str]) -> tuple[float, dict[str, Any]]:
        score = 0.0
        for stim_qubit, label in stim_to_hardware.items():
            score += _node_error(hardware, label, roles[stim_qubit], weights)

        direct_edges = 0
        routed_edges = 0
        disconnected_edges = 0
        max_route_distance = 0
        max_coupler_error = 0.0

        for (stim_a, stim_b), count in interaction_counts.items():
            left = stim_to_hardware[stim_a]
            right = stim_to_hardware[stim_b]
            path = shortest_paths.get(left, {}).get(right)
            if path is None:
                score += disconnected_penalty * count
                disconnected_edges += 1
                continue

            distance = len(path) - 1
            max_route_distance = max(max_route_distance, distance)
            if distance == 1:
                direct_edges += 1
            else:
                routed_edges += 1
                score += route_distance_weight * count * (distance - 1)

            path_error = 0.0
            for index in range(distance):
                labels = _sorted_pair(path[index], path[index + 1])
                coupler_error = hardware["couplers"].get(labels, 0.0)
                max_coupler_error = max(max_coupler_error, coupler_error)
                path_error += coupler_error
            score += float(weights.get("two_qubit", 1.0)) * count * path_error
        score += float(weights.get("max_coupler", 0.0)) * max_coupler_error

        return score, {
            "direct_code_edges": direct_edges,
            "routed_code_edges": routed_edges,
            "disconnected_code_edges": disconnected_edges,
            "max_route_distance": max_route_distance,
            "max_coupler_error": max_coupler_error,
        }

    return score_assignment


def _assignment_to_mapping(
    stim_to_hardware: dict[int, str],
    stim_to_dense: dict[int, int],
    roles: dict[int, str],
    hardware: dict[str, Any],
    score: float,
) -> dict[str, Any]:
    dense_to_hardware = {
        dense: stim_to_hardware[stim_qubit]
        for stim_qubit, dense in stim_to_dense.items()
    }
    initial_layout = [
        hardware["qubits"][dense_to_hardware[dense]]["index"]
        for dense in range(len(dense_to_hardware))
    ]
    return {
        "qpu": hardware["qpu"],
        "score": score,
        "initial_layout": initial_layout,
        "stim_to_hardware": {str(key): value for key, value in sorted(stim_to_hardware.items())},
        "dense_to_hardware": {str(key): value for key, value in sorted(dense_to_hardware.items())},
        "data_hardware": sorted(
            (label for stim_qubit, label in stim_to_hardware.items() if roles[stim_qubit] == "data"),
            key=_label_sort_key,
        ),
        "ancilla_hardware": sorted(
            (label for stim_qubit, label in stim_to_hardware.items() if roles[stim_qubit] == "ancilla"),
            key=_label_sort_key,
        ),
    }


def _node_error(hardware: dict[str, Any], label: str, role: str, weights: dict[str, float]) -> float:
    errors = hardware["qubits"][label]["errors"]
    score = (
        float(weights.get("one_qubit", 1.0)) * float(errors.get("one_qubit", 0.0))
        + float(weights.get("idle", 1.0)) * float(errors.get("idle", 0.0))
    )
    if role == "ancilla":
        score += float(weights.get("measurement", 1.0)) * float(errors.get("measurement", 0.0))
        score += float(weights.get("reset", 1.0)) * float(errors.get("reset", 0.0))
        score += float(weights.get("qnd", 1.0)) * float(errors.get("qnd", 0.0))
    return score


def _code_nodes_by_position(patch_coords: dict[int, tuple[int, int]]) -> list[int]:
    return sorted(patch_coords, key=lambda node: (patch_coords[node][0], patch_coords[node][1], node))


def _normalized_points(points: dict[int, tuple[int, int]]) -> dict[int, np.ndarray]:
    raw = np.array(list(points.values()), dtype=float)
    center = raw.mean(axis=0)
    scale = max(raw[:, 0].max() - raw[:, 0].min(), raw[:, 1].max() - raw[:, 1].min(), 1.0)
    normalized = (raw - center) / scale
    return {
        node: normalized[index]
        for index, node in enumerate(points)
    }


def _coordinate_transforms(points: dict[int, np.ndarray]) -> list[dict[int, np.ndarray]]:
    transforms = []
    matrices = [
        np.array([[1, 0], [0, 1]]),
        np.array([[1, 0], [0, -1]]),
        np.array([[-1, 0], [0, 1]]),
        np.array([[-1, 0], [0, -1]]),
        np.array([[0, 1], [1, 0]]),
        np.array([[0, 1], [-1, 0]]),
        np.array([[0, -1], [1, 0]]),
        np.array([[0, -1], [-1, 0]]),
    ]
    for matrix in matrices:
        transforms.append({
            node: matrix @ point
            for node, point in points.items()
        })
    return transforms


def _parse_iqm_observation_set(calibration: dict[str, Any]) -> dict[str, Any]:
    qubit_labels = set()
    one_qubit_errors: dict[str, list[float]] = {}
    measurement_errors: dict[str, list[float]] = {}
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
            if "ssro.measure" in field and field.endswith(("error_0_to_1", "error_1_to_0")):
                measurement_errors.setdefault(label, []).append(value)
            elif "ssro.measure" in field and field.endswith(".fidelity"):
                measurement_errors.setdefault(label, []).append(1.0 - value)
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
            pair = tuple(sorted(labels[:2], key=_index_from_label))
            priority = 0 if ".irb.cz." in field else 1
            coupler_candidates.setdefault(pair, []).append((priority, 1.0 - value))

    qubits = {}
    for label in sorted(qubit_labels, key=_index_from_label):
        qnd_error = 1.0 - min(qnd_values[label]) if label in qnd_values else 0.0
        idle_time = t2_echo_times.get(label) or t2_times.get(label)
        idle_error = 1.0 - np.exp(-DEFAULT_ROUND_SECONDS / idle_time) if idle_time else 0.0
        qubits[label] = {
            "label": label,
            "index": _index_from_label(label),
            "errors": {
                "one_qubit": min(one_qubit_errors.get(label, [0.0])),
                "measurement": max(measurement_errors.get(label, [0.0])),
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


def _index_from_label(label: str) -> int:
    if label.upper().startswith("QB"):
        return int(label[2:]) - 1
    raise ValueError(f"Qubit label {label!r} needs explicit qiskit index")


def _label_sort_key(label: str) -> tuple[int, int | str]:
    if label.upper().startswith("QB") and label[2:].isdigit():
        return (0, int(label[2:]))
    return (1, label)


def _sorted_pair(left: str, right: str) -> tuple[str, str]:
    first, second = sorted((left, right), key=_label_sort_key)
    return (first, second)


def _normalize_qubit_label(label: str | int) -> str:
    if isinstance(label, int):
        return f"QB{label}"
    text = str(label).strip().upper()
    if text.startswith("QB"):
        return f"QB{int(text[2:])}"
    if text.isdigit():
        return f"QB{int(text)}"
    raise ValueError(f"Invalid qubit label in exclude_qubits: {label!r}")
