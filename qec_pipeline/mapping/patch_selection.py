from __future__ import annotations

import random
from collections import Counter
from typing import Any

import networkx as nx
import numpy as np
import stim
from scipy.optimize import linear_sum_assignment

from qec_pipeline.mapping.calibration import (
    build_hardware_graph,
    filter_hardware_qubits,
    label_sort_key,
    load_calibration,
    normalize_qubit_label,
    parse_hardware,
    sorted_pair,
)


def select_calibration_best_patch(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
    calibration: dict[str, Any],
    weights: dict[str, float] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the lowest-score hardware patch for a Stim surface-code circuit."""
    candidates = rank_calibration_best_patches(
        stim_circuit,
        stim_to_dense,
        calibration,
        weights=weights,
        options=options,
    )
    if not candidates:
        raise ValueError("No valid hardware patch found for this circuit and calibration data")
    return candidates[0]


def rank_calibration_best_patches(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
    calibration: dict[str, Any],
    weights: dict[str, float] | None = None,
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return all valid native patches sorted by mapping score."""
    weights = weights or {}
    options = options or {}
    interaction_counts, roles, hardware = _problem(stim_circuit, stim_to_dense, calibration, options)

    if not hardware["coord_to_label"]:
        candidates = _rank_graph_patches(stim_to_dense, interaction_counts, roles, hardware, weights)
        for candidate in candidates:
            candidate["strategy"] = "calibration_best_patch"
            candidate["excluded_qubits"] = hardware.get("excluded_qubits", [])
        return candidates

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

    candidates = sorted(candidates, key=lambda item: item["score"])
    for candidate in candidates:
        candidate["num_candidates"] = len(candidates)
        candidate["strategy"] = "calibration_best_patch"
        candidate["excluded_qubits"] = hardware.get("excluded_qubits", [])
    return candidates


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
    interaction_counts, roles, hardware = _problem(stim_circuit, stim_to_dense, calibration, options)
    hardware_graph = build_hardware_graph(hardware)
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
    """Return mapping metadata for the configured strategy (a pinned patch takes precedence)."""
    strategy = mapping.get("strategy", "none")
    if strategy in {"none", None}:
        return None
    if not mapping.get("calibration_file"):
        raise ValueError(f"mapping.calibration_file is required for {strategy}")
    calibration = load_calibration(mapping["calibration_file"])
    kwargs = {"weights": mapping.get("weights"), "options": mapping.get("options")}

    pinned = (mapping.get("hardware_patch") or {}).get("stim_to_hardware")
    if pinned:
        return select_fixed_stim_to_hardware_patch(stim_circuit, stim_to_dense, calibration, pinned, **kwargs)
    selectors = {
        "calibration_best_patch": select_calibration_best_patch,
        "calibration_routed_layout": select_calibration_routed_layout,
    }
    if strategy not in selectors:
        raise NotImplementedError(f"mapping strategy not implemented: {strategy}")
    return selectors[strategy](stim_circuit, stim_to_dense, calibration, **kwargs)


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
    interaction_counts, roles, hardware = _problem(stim_circuit, stim_to_dense, calibration, options)

    normalized = {int(stim): normalize_qubit_label(label) for stim, label in stim_to_hardware.items()}
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
        allow_routing=bool(options.get("allow_routing", False)),
    )
    if selected is None:
        raise ValueError("fixed hardware patch is missing required native couplers")

    selected["strategy"] = "fixed_stim_to_hardware"
    selected["selection"] = "fixed_stim_to_hardware"
    selected["source_schema"] = hardware["source_schema"]
    selected["num_candidates"] = 1
    selected["excluded_qubits"] = hardware.get("excluded_qubits", [])
    return selected


def _problem(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
    calibration: dict[str, Any],
    options: dict[str, Any],
) -> tuple[Counter[tuple[int, int]], dict[int, str], dict[str, Any]]:
    """Interaction counts, qubit roles, and the usable hardware table for one selection."""
    hardware = filter_hardware_qubits(parse_hardware(calibration), options.get("exclude_qubits", []) or [])
    return two_qubit_interaction_counts(stim_circuit), surface_code_qubit_roles(stim_circuit, stim_to_dense), hardware


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
        targets = instruction.targets_copy()
        for index in range(0, len(targets), 2):
            left, right = targets[index], targets[index + 1]
            if not (left.is_qubit_target and right.is_qubit_target):
                continue  # classically controlled gate (e.g. feed-forward reset), not an interaction
            pair = tuple(sorted((left.value, right.value)))
            counts[pair] += 1
    return counts


def surface_code_qubit_roles(
    stim_circuit: stim.Circuit,
    stim_to_dense: dict[int, int],
) -> dict[int, str]:
    """Return `data` for qubits in the final measurement layer, `ancilla` for other measured qubits.

    Works for every mid-circuit reset strategy (MR, M + feed-forward, M only): data
    qubits are read out once at the end, ancillas are measured in earlier layers.
    """
    measurement_names = {"M", "MX", "MY", "MR", "MRX", "MRY", "MZ", "MRZ"}
    instructions = list(stim_circuit.flattened())
    measured: set[int] = set()
    for instruction in instructions:
        if instruction.name in measurement_names:
            measured.update(target.value for target in instruction.targets_copy() if target.is_qubit_target)
    final_layer: set[int] = set()
    final_name = None
    for instruction in reversed(instructions):
        if instruction.name in measurement_names and final_name in {None, instruction.name}:
            final_name = instruction.name
            final_layer.update(target.value for target in instruction.targets_copy() if target.is_qubit_target)
        elif final_name is not None:
            break  # anything else (detectors, gates, another basis) ends the final layer
    ancillas = measured - final_layer

    return {
        stim_qubit: "ancilla" if stim_qubit in ancillas else "data"
        for stim_qubit in stim_to_dense
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


def _rank_graph_patches(
    stim_to_dense: dict[int, int],
    interaction_counts: Counter[tuple[int, int]],
    roles: dict[int, str],
    hardware: dict[str, Any],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Find native hardware subgraphs matching the generated interaction graph."""
    code_graph = nx.Graph()
    code_graph.add_nodes_from(stim_to_dense)
    code_graph.add_edges_from(interaction_counts)

    hardware_graph = build_hardware_graph(hardware)

    matcher = nx.algorithms.isomorphism.GraphMatcher(hardware_graph, code_graph)
    candidates = []

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
        candidates.append(candidate)

    candidates = sorted(candidates, key=lambda item: item["score"])
    for candidate in candidates:
        candidate["num_candidates"] = len(candidates)
        candidate["selection"] = "native_graph"
        candidate["source_schema"] = hardware["source_schema"]
    return candidates


def _score_assignment(
    stim_to_hardware: dict[int, str],
    stim_to_dense: dict[int, int],
    interaction_counts: Counter[tuple[int, int]],
    roles: dict[int, str],
    hardware: dict[str, Any],
    weights: dict[str, float],
    allow_routing: bool = False,
) -> dict[str, Any] | None:
    score = 0.0
    for stim_qubit, label in stim_to_hardware.items():
        score += _node_error(hardware, label, roles[stim_qubit], weights)

    missing_couplers = []
    max_coupler_error = 0.0
    routed_code_edges = 0
    expected_swap_count = 0
    max_route_distance = 1
    hardware_graph = build_hardware_graph(hardware) if allow_routing else None
    for (stim_a, stim_b), count in interaction_counts.items():
        labels = sorted_pair(stim_to_hardware[stim_a], stim_to_hardware[stim_b])
        if hardware["has_couplers"] and labels not in hardware["couplers"]:
            missing_couplers.append(labels)
            if allow_routing and hardware_graph is not None:
                try:
                    path = nx.shortest_path(hardware_graph, labels[0], labels[1])
                    distance = len(path) - 1
                    routed_code_edges += 1
                    max_route_distance = max(max_route_distance, distance)
                    expected_swap_count += max(0, distance - 1)
                    score += float(weights.get("route_distance", 0.2)) * count * max(0, distance - 1)
                    for index in range(len(path) - 1):
                        edge = sorted_pair(path[index], path[index + 1])
                        coupler_error = hardware["couplers"].get(edge, 0.0)
                        max_coupler_error = max(max_coupler_error, coupler_error)
                        score += float(weights.get("two_qubit", 1.0)) * count * coupler_error
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    return None
            continue
        coupler_error = hardware["couplers"].get(labels, 0.0)
        max_coupler_error = max(max_coupler_error, coupler_error)
        score += float(weights.get("two_qubit", 1.0)) * count * coupler_error
    score += float(weights.get("max_coupler", 0.0)) * max_coupler_error

    if missing_couplers and not allow_routing:
        return None

    unique_code_edges = len(interaction_counts)
    return _assignment_to_mapping(stim_to_hardware, stim_to_dense, roles, hardware, score) | {
        "unique_code_edges": unique_code_edges,
        "native_code_edges": unique_code_edges - len(missing_couplers),
        "routed_code_edges": routed_code_edges,
        "missing_couplers": [list(pair) for pair in missing_couplers],
        "max_route_distance": max_route_distance,
        "total_code_two_qubit_interactions": int(sum(interaction_counts.values())),
        "expected_swap_count": expected_swap_count,
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
            for row, col in zip(rows, cols, strict=True)
        }
        assignments.append(assignment)

    label_sorted = sorted(hardware_labels, key=label_sort_key)
    best_49 = sorted(
        hardware_labels,
        key=lambda label: (_node_error(hardware, label, "ancilla", weights), label_sort_key(label)),
    )[: len(code_nodes)]
    assignments.append(dict(zip(code_nodes, label_sorted[: len(code_nodes)], strict=True)))
    assignments.append(dict(zip(code_nodes, sorted(best_49, key=label_sort_key), strict=True)))

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
                labels = sorted_pair(path[index], path[index + 1])
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
            key=label_sort_key,
        ),
        "ancilla_hardware": sorted(
            (label for stim_qubit, label in stim_to_hardware.items() if roles[stim_qubit] == "ancilla"),
            key=label_sort_key,
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


