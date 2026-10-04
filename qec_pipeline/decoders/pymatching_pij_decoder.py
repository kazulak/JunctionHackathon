"""MWPM with edge probabilities estimated from the detection events themselves (p_ij).

Method of Google Quantum AI, "Exponential suppression of bit or phase errors with
cyclic error correction", Nature 595 (2021), and "Suppressing quantum errors by
scaling a surface code logical qubit", Nature 614 (2023), Sec. XII A:

- the *structure* of the matching graph comes from the circuit's detector error model;
- each edge's *probability* is re-estimated from correlations between detection events;
- to avoid fitting the decoder to the data it decodes, probabilities are estimated on
  some shots and used on the others (cross-fitting; Google used odd/even halves).

Pairwise edge between detectors i and j:

    p_ij = 1/2 - 1/2 * sqrt(1 - 4 (<x_i x_j> - <x_i><x_j>) / (1 - 2<x_i> - 2<x_j> + 4<x_i x_j>))

Boundary edge of detector i, from the firing rate of i and its other edges e:

    1 - 2 p_i = (1 - 2<x_i>) / prod_e (1 - 2 p_e)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pymatching

from qec_pipeline.analysis.metrics import binomial_standard_error

MIN_PROBABILITY = 1e-6
MAX_PROBABILITY = 0.5 - 1e-6


def decode_with_pymatching_pij(
    decoder: dict[str, Any],
    circuit: tuple,
    syndromes: tuple,
) -> tuple:
    _stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, _syndrome_info = syndromes
    options = decoder.get("options", {}) or {}
    folds = int(options.get("folds", 2))
    if folds < 2:
        raise ValueError("pymatching_pij needs folds >= 2 so edge estimates never use the decoded shots")

    detection_events = np.asarray(detection_events, dtype=bool)
    observable_flips = _as_2d_bool(observable_flips)
    prior = pymatching.Matching.from_detector_error_model(detector_model)
    shots = len(detection_events)

    predicted = np.zeros_like(observable_flips, dtype=bool)
    fold_summaries = []
    for fold in range(folds):
        evaluation = np.arange(shots) % folds == fold  # interleaved, robust to drift
        training = ~evaluation
        probabilities, summary = estimate_edge_probabilities(prior, detection_events[training])
        matching = matching_with_probabilities(prior, probabilities)
        predicted[evaluation] = _as_2d_bool(matching.decode_batch(detection_events[evaluation]))
        fold_summaries.append(summary)

    logical_failures = np.logical_xor(predicted, observable_flips).any(axis=1)
    ler = float(logical_failures.mean()) if shots else 0.0
    uncertainty = binomial_standard_error(ler, shots) if shots else 0.0
    decoder_info = {
        "decoder": decoder["name"],
        "shots": shots,
        "logical_failures": int(logical_failures.sum()),
        "num_observables": int(circuit_info["num_observables"]),
        "note": "MWPM with p_ij edge probabilities estimated on other folds (Google 2021/2023).",
        "folds": folds,
        "fold_summaries": fold_summaries,
    }
    return predicted, logical_failures, ler, uncertainty, decoder_info


def estimate_edge_probabilities(
    prior: pymatching.Matching,
    detection_events: np.ndarray,
) -> tuple[dict[tuple[int, int | None], float], dict[str, Any]]:
    """Estimate the probability of every edge in `prior` from detection-event statistics."""
    events = np.asarray(detection_events, dtype=float)
    mean = events.mean(axis=0)
    edges = prior.edges()
    estimates: dict[tuple[int, int | None], float] = {}
    fallbacks = 0

    for left, right, data in edges:
        if right is None:
            continue
        joint = float(np.mean(events[:, left] * events[:, right]))
        denominator = 1.0 - 2.0 * mean[left] - 2.0 * mean[right] + 4.0 * joint
        radicand = 1.0 - 4.0 * (joint - mean[left] * mean[right]) / denominator if denominator > 0 else -1.0
        if radicand < 0 or not np.isfinite(radicand):
            estimates[(left, right)] = _clip(data["error_probability"])
            fallbacks += 1
            continue
        estimates[(left, right)] = _clip(0.5 - 0.5 * np.sqrt(radicand))

    for left, right, data in edges:
        if right is not None:
            continue
        others = 1.0
        for (a, b), probability in estimates.items():
            if b is not None and left in (a, b):
                others *= 1.0 - 2.0 * probability
        ratio = (1.0 - 2.0 * mean[left]) / others if others > 0 else -1.0
        if not 0.0 < ratio <= 1.0:
            estimates[(left, None)] = _clip(data["error_probability"])
            fallbacks += 1
            continue
        estimates[(left, None)] = _clip(0.5 * (1.0 - ratio))

    prior_probabilities = np.array([data["error_probability"] for _l, _r, data in edges])
    new_probabilities = np.array([estimates[(left, right)] for left, right, _data in edges])
    summary = {
        "training_shots": int(len(events)),
        "edges": len(edges),
        "fallback_edges": fallbacks,
        "mean_prior_probability": float(prior_probabilities.mean()) if len(edges) else 0.0,
        "mean_estimated_probability": float(new_probabilities.mean()) if len(edges) else 0.0,
    }
    return estimates, summary


def matching_with_probabilities(
    prior: pymatching.Matching,
    probabilities: dict[tuple[int, int | None], float],
) -> pymatching.Matching:
    """Same graph and observables as `prior`, with re-estimated edge probabilities."""
    matching = pymatching.Matching()
    for left, right, data in prior.edges():
        probability = probabilities[(left, right)]
        weight = float(np.log((1.0 - probability) / probability))
        if right is None:
            matching.add_boundary_edge(
                left,
                fault_ids=data["fault_ids"],
                weight=weight,
                error_probability=probability,
                merge_strategy="replace",
            )
        else:
            matching.add_edge(
                left,
                right,
                fault_ids=data["fault_ids"],
                weight=weight,
                error_probability=probability,
                merge_strategy="replace",
            )
    if matching.num_detectors < prior.num_detectors:
        matching.set_boundary_nodes(set())
    return matching


def _clip(probability: float) -> float:
    return float(min(max(probability, MIN_PROBABILITY), MAX_PROBABILITY))


def _as_2d_bool(array: object) -> np.ndarray:
    result = np.asarray(array, dtype=bool)
    if result.ndim == 1:
        return result.reshape((-1, 1))
    return result
