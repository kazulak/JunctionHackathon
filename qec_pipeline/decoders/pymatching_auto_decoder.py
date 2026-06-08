from __future__ import annotations

from typing import Any

import numpy as np

from qec_pipeline.decoders.pymatching_decoder import (
    decode_detection_events,
    detector_model_with_uniform_noise,
)


def decode_with_pymatching_auto(
    decoder: dict[str, Any],
    circuit: tuple,
    syndromes: tuple,
) -> tuple:
    """Try several simple MWPM models and report the best one on this run."""
    stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, syndrome_info = syndromes
    options = decoder.get("options", {}) or {}
    detection_events = np.asarray(detection_events, dtype=bool)
    observable_flips = _as_2d_bool(observable_flips)

    mask = _postselection_mask(detection_events, options)
    used_detection_events = detection_events[mask]
    used_observable_flips = observable_flips[mask]

    candidates = []
    mwpm_candidates = []
    configured_candidate = (
        _decode_candidate(
            "calibrated_or_configured",
            detector_model,
            used_detection_events,
            used_observable_flips,
        )
    )
    candidates.append(configured_candidate)
    mwpm_candidates.append(configured_candidate)

    if bool(options.get("include_correlated_matching", False)):
        correlated_candidate = _decode_candidate(
            "correlated_calibrated_or_configured",
            detector_model,
            used_detection_events,
            used_observable_flips,
            enable_correlations=True,
        )
        candidates.append(correlated_candidate)
        mwpm_candidates.append(correlated_candidate)

    for probability in options.get("uniform_probabilities", []):
        uniform_model = detector_model_with_uniform_noise(stim_circuit, float(probability))
        candidate = _decode_candidate(
            f"uniform_p={float(probability):g}",
            uniform_model,
            used_detection_events,
            used_observable_flips,
        )
        candidates.append(candidate)
        mwpm_candidates.append(candidate)
        if bool(options.get("include_correlated_matching", False)):
            correlated_candidate = _decode_candidate(
                f"correlated_uniform_p={float(probability):g}",
                uniform_model,
                used_detection_events,
                used_observable_flips,
                enable_correlations=True,
            )
            candidates.append(correlated_candidate)
            mwpm_candidates.append(correlated_candidate)

    candidates.extend(
        _ensemble_candidates(
            mwpm_candidates,
            used_observable_flips,
            options,
        )
    )
    candidates.extend(
        _gated_no_correction_candidates(
            mwpm_candidates,
            used_detection_events,
            used_observable_flips,
            options,
        )
    )

    if bool(options.get("include_no_correction", True)):
        logical_failures = np.asarray(used_observable_flips, dtype=bool).any(axis=1)
        shots = int(len(logical_failures))
        ler = float(logical_failures.mean()) if shots else 0.0
        uncertainty = _binomial_standard_error(ler, shots)
        candidates.append(
            {
                "name": "no_correction",
                "predicted_observables": np.zeros_like(used_observable_flips, dtype=bool),
                "logical_failures": logical_failures,
                "ler": ler,
                "uncertainty": uncertainty,
            }
        )

    best, candidate_selection_info = _select_candidate(candidates, options)
    decoder_info = {
        "decoder": decoder["name"],
        "selected_candidate": best["name"],
        "shots": int(len(best["logical_failures"])),
        "original_shots": int(len(detection_events)),
        "kept_shots": int(mask.sum()),
        "postselection_fraction": float(mask.mean()) if len(mask) else 1.0,
        "logical_failures": int(best["logical_failures"].sum()),
        "num_observables": int(circuit_info["num_observables"]),
        "noise_model": circuit_info.get("noise_model"),
        "mean_syndrome_weight": syndrome_info.get("mean_syndrome_weight"),
        **candidate_selection_info,
        "candidates": [
            {
                "name": item["name"],
                "ler": float(item["ler"]),
                "uncertainty": float(item["uncertainty"]),
                "logical_failures": int(item["logical_failures"].sum()),
                "shots": int(len(item["logical_failures"])),
                **_candidate_split_info(item),
            }
            for item in candidates
        ],
    }

    return (
        best["predicted_observables"],
        best["logical_failures"],
        float(best["ler"]),
        float(best["uncertainty"]),
        decoder_info,
    )


def _decode_candidate(
    name: str,
    detector_model: object,
    detection_events: np.ndarray,
    observable_flips: np.ndarray,
    enable_correlations: bool = False,
) -> dict[str, Any]:
    predicted, logical_failures, ler, uncertainty = decode_detection_events(
        detector_model,
        detection_events,
        observable_flips,
        enable_correlations=enable_correlations,
    )
    return {
        "name": name,
        "predicted_observables": predicted,
        "logical_failures": logical_failures,
        "ler": ler,
        "uncertainty": uncertainty,
    }


def _ensemble_candidates(
    mwpm_candidates: list[dict[str, Any]],
    observable_flips: np.ndarray,
    options: dict[str, Any],
) -> list[dict[str, Any]]:
    """Add simple majority-vote MWPM ensembles.

    This is a cheap local analogue of matching ensembles: several DEM priors
    produce predictions, then the observable prediction is majority-voted.
    """
    if not bool(options.get("include_matching_ensembles", False)):
        return []
    if len(mwpm_candidates) < 3:
        return []

    groups = [("ensemble_all_mwpm", mwpm_candidates)]
    uniform_candidates = [
        candidate for candidate in mwpm_candidates if candidate["name"].startswith("uniform_p=")
    ]
    if len(uniform_candidates) >= 3:
        groups.append(("ensemble_uniform_mwpm", uniform_candidates))

    result = []
    observable_flips = _as_2d_bool(observable_flips)
    for name, group in groups:
        predicted = _majority_vote_predictions(
            [candidate["predicted_observables"] for candidate in group]
        )
        logical_failures = np.logical_xor(predicted, observable_flips).any(axis=1)
        shots = int(len(logical_failures))
        ler = float(logical_failures.mean()) if shots else 0.0
        uncertainty = _binomial_standard_error(ler, shots)
        result.append(
            {
                "name": name,
                "predicted_observables": predicted,
                "logical_failures": logical_failures,
                "ler": ler,
                "uncertainty": uncertainty,
            }
        )
    return result


def _majority_vote_predictions(predictions: list[np.ndarray]) -> np.ndarray:
    stacked = np.stack([_as_2d_bool(prediction) for prediction in predictions])
    votes = stacked.sum(axis=0)
    half = len(predictions) / 2
    majority = votes > half
    if len(predictions) % 2 == 0:
        ties = votes == half
        majority[ties] = stacked[0][ties]
    return majority


def _select_candidate(
    candidates: list[dict[str, Any]],
    options: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = str(options.get("candidate_selection_mode", "current_batch")).lower()
    if mode in {"current_batch", "best_on_current_batch"}:
        best = min(candidates, key=lambda item: item["ler"])
        return best, {"candidate_selection": "best_on_current_batch"}

    if mode == "kfold":
        return _select_candidate_kfold(candidates, options)

    if mode != "holdout":
        raise ValueError(
            "candidate_selection_mode must be 'current_batch', 'holdout', or 'kfold'"
        )

    shots = int(len(candidates[0]["logical_failures"])) if candidates else 0
    if shots < 2:
        best = min(candidates, key=lambda item: item["ler"])
        return best, {
            "candidate_selection": "holdout_fallback_current_batch",
            "selection_shots": shots,
            "evaluation_shots": 0,
        }

    selection_fraction = float(options.get("selection_fraction", 0.5))
    if not 0.0 < selection_fraction < 1.0:
        raise ValueError("selection_fraction must be between 0 and 1")

    selection_shots = int(round(shots * selection_fraction))
    selection_shots = min(max(selection_shots, 1), shots - 1)

    rng = np.random.default_rng(int(options.get("selection_seed", 1)))
    indices = np.arange(shots)
    rng.shuffle(indices)

    selection_mask = np.zeros(shots, dtype=bool)
    selection_mask[indices[:selection_shots]] = True
    evaluation_mask = ~selection_mask

    for candidate in candidates:
        selection_failures = candidate["logical_failures"][selection_mask]
        evaluation_failures = candidate["logical_failures"][evaluation_mask]
        candidate["selection_ler"] = _mean_bool(selection_failures)
        candidate["selection_logical_failures"] = int(selection_failures.sum())
        candidate["selection_shots"] = int(selection_failures.size)
        candidate["evaluation_ler"] = _mean_bool(evaluation_failures)
        candidate["evaluation_logical_failures"] = int(evaluation_failures.sum())
        candidate["evaluation_shots"] = int(evaluation_failures.size)

    selected = min(
        candidates,
        key=lambda item: (item["selection_ler"], item["evaluation_ler"]),
    )
    reported = {
        "name": selected["name"],
        "predicted_observables": selected["predicted_observables"][evaluation_mask],
        "logical_failures": selected["logical_failures"][evaluation_mask],
        "ler": float(selected["evaluation_ler"]),
        "uncertainty": _binomial_standard_error(
            float(selected["evaluation_ler"]),
            int(selected["evaluation_shots"]),
        ),
    }
    info = {
        "candidate_selection": "holdout",
        "selection_fraction": float(selection_fraction),
        "selection_shots": int(selection_shots),
        "evaluation_shots": int(evaluation_mask.sum()),
        "selection_seed": int(options.get("selection_seed", 1)),
        "selected_candidate_selection_ler": float(selected["selection_ler"]),
        "selected_candidate_evaluation_ler": float(selected["evaluation_ler"]),
    }
    return reported, info


def _select_candidate_kfold(
    candidates: list[dict[str, Any]],
    options: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    shots = int(len(candidates[0]["logical_failures"])) if candidates else 0
    folds = int(options.get("candidate_selection_folds", 5))
    if folds < 2:
        raise ValueError("candidate_selection_folds must be at least 2")
    if shots < folds:
        best = min(candidates, key=lambda item: item["ler"])
        return best, {
            "candidate_selection": "kfold_fallback_current_batch",
            "candidate_selection_folds": folds,
        }

    rng = np.random.default_rng(int(options.get("selection_seed", 1)))
    shuffled_indices = np.arange(shots)
    rng.shuffle(shuffled_indices)
    fold_indices = np.array_split(shuffled_indices, folds)

    predicted = np.zeros_like(candidates[0]["predicted_observables"], dtype=bool)
    logical_failures = np.zeros(shots, dtype=bool)
    selected_names = []
    fold_rows = []

    for fold_index, evaluation_indices in enumerate(fold_indices):
        evaluation_mask = np.zeros(shots, dtype=bool)
        evaluation_mask[evaluation_indices] = True
        selection_mask = ~evaluation_mask

        fold_scores = []
        for candidate in candidates:
            selection_failures = candidate["logical_failures"][selection_mask]
            evaluation_failures = candidate["logical_failures"][evaluation_mask]
            fold_scores.append(
                {
                    "candidate": candidate,
                    "selection_ler": _mean_bool(selection_failures),
                    "selection_logical_failures": int(selection_failures.sum()),
                    "selection_shots": int(selection_failures.size),
                    "evaluation_ler": _mean_bool(evaluation_failures),
                    "evaluation_logical_failures": int(evaluation_failures.sum()),
                    "evaluation_shots": int(evaluation_failures.size),
                }
            )

        selected = min(
            fold_scores,
            key=lambda item: (item["selection_ler"], item["evaluation_ler"]),
        )
        candidate = selected["candidate"]
        predicted[evaluation_mask] = candidate["predicted_observables"][evaluation_mask]
        logical_failures[evaluation_mask] = candidate["logical_failures"][evaluation_mask]
        selected_names.append(candidate["name"])
        fold_rows.append(
            {
                "fold": fold_index,
                "selected_candidate": candidate["name"],
                "selection_ler": float(selected["selection_ler"]),
                "selection_logical_failures": int(selected["selection_logical_failures"]),
                "selection_shots": int(selected["selection_shots"]),
                "evaluation_ler": float(selected["evaluation_ler"]),
                "evaluation_logical_failures": int(selected["evaluation_logical_failures"]),
                "evaluation_shots": int(selected["evaluation_shots"]),
            }
        )

    ler = _mean_bool(logical_failures)
    reported = {
        "name": "kfold_selected_candidates",
        "predicted_observables": predicted,
        "logical_failures": logical_failures,
        "ler": ler,
        "uncertainty": _binomial_standard_error(ler, shots),
    }
    info = {
        "candidate_selection": "kfold",
        "candidate_selection_folds": folds,
        "selection_seed": int(options.get("selection_seed", 1)),
        "fold_selected_candidates": fold_rows,
        "unique_selected_candidates": sorted(set(selected_names)),
    }
    return reported, info


def _candidate_split_info(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "selection_ler",
        "selection_logical_failures",
        "selection_shots",
        "evaluation_ler",
        "evaluation_logical_failures",
        "evaluation_shots",
    ]
    return {key: candidate[key] for key in keys if key in candidate}


def _mean_bool(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(values.mean())


def _gated_no_correction_candidates(
    mwpm_candidates: list[dict[str, Any]],
    detection_events: np.ndarray,
    observable_flips: np.ndarray,
    options: dict[str, Any],
) -> list[dict[str, Any]]:
    """Use no correction on low-syndrome shots and MWPM otherwise.

    This is a cheap diagnostic inspired by detector-rate analysis: if low
    syndrome-weight shots are already reliable, avoid over-correcting them.
    """
    if not mwpm_candidates:
        return []

    weights = detection_events.sum(axis=1)
    observable_flips = _as_2d_bool(observable_flips)
    thresholds = _gated_thresholds(weights, options)
    candidates = []
    for threshold_name, threshold in thresholds:
        low_syndrome = weights <= threshold
        if not low_syndrome.any() or low_syndrome.all():
            continue
        for candidate in mwpm_candidates:
            predicted = np.array(candidate["predicted_observables"], dtype=bool, copy=True)
            predicted[low_syndrome] = False
            logical_failures = np.logical_xor(predicted, observable_flips).any(axis=1)
            shots = int(len(logical_failures))
            ler = float(logical_failures.mean()) if shots else 0.0
            uncertainty = _binomial_standard_error(ler, shots)
            candidates.append(
                {
                    "name": f"{candidate['name']}|no_correction_for_{threshold_name}",
                    "predicted_observables": predicted,
                    "logical_failures": logical_failures,
                    "ler": ler,
                    "uncertainty": uncertainty,
                }
            )
    return candidates


def _gated_thresholds(
    syndrome_weights: np.ndarray,
    options: dict[str, Any],
) -> list[tuple[str, int]]:
    thresholds: list[tuple[str, int]] = []
    for quantile in options.get("gated_no_correction_quantiles", []):
        q = float(quantile)
        threshold = int(np.quantile(syndrome_weights, q))
        thresholds.append((f"weight_le_{threshold}_q{q:g}", threshold))
    for threshold in options.get("gated_no_correction_max_weights", []):
        value = int(threshold)
        thresholds.append((f"weight_le_{value}", value))

    unique = []
    seen = set()
    for name, threshold in thresholds:
        if threshold in seen:
            continue
        unique.append((name, threshold))
        seen.add(threshold)
    return unique


def _postselection_mask(detection_events: np.ndarray, options: dict[str, Any]) -> np.ndarray:
    weights = detection_events.sum(axis=1)
    if "postselect_max_syndrome_weight" in options:
        return weights <= int(options["postselect_max_syndrome_weight"])
    if "postselect_weight_quantile" in options:
        quantile = float(options["postselect_weight_quantile"])
        threshold = int(np.quantile(weights, quantile))
        return weights <= threshold
    return np.ones(len(detection_events), dtype=bool)


def _as_2d_bool(array: object) -> np.ndarray:
    result = np.asarray(array, dtype=bool)
    if result.ndim == 1:
        return result.reshape((-1, 1))
    return result


def _binomial_standard_error(ler: float, shots: int) -> float:
    if shots <= 0:
        return 0.0
    return float((ler * (1.0 - ler) / shots) ** 0.5)
