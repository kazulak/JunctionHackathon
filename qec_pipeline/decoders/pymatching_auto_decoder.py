"""Decoder-candidate study: several MWPM variants, one reported result.

Candidates (each switched on by an option):
    calibrated_or_configured   MWPM on the circuit's detector error model (always)
    correlated_*               correlated matching (`include_correlated_matching`)
    uniform_p=...              MWPM with uniform-noise priors (`uniform_probabilities`)
    ensemble_*                 majority vote of MWPM variants (`include_matching_ensembles`)
    ...|no_correction_for_*    no correction on low-syndrome shots (`gated_no_correction_*`)
    no_correction              raw observable (`include_no_correction`, default on)

Selection (`candidate_selection_mode`):
    kfold (default)   choose on k-1 folds, report on the held-out fold, for every fold
    holdout           choose on one split, report on the other
    current_batch     choose and report on the same shots: optimistic (winner's curse),
                      flagged `selection_is_in_sample`

Postselection (`postselect_max_syndrome_weight` / `postselect_weight_quantile`) keeps only
low-syndrome shots before decoding; it is a diagnostic, not a logical-memory result.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from qec_pipeline.decoders.pymatching_decoder import decode_detection_events, detector_model_with_uniform_noise
from qec_pipeline.decoders.scoring import as_2d_bool, score_predictions, uncertainty

DEFAULT_SELECTION_MODE = "kfold"


def decode_with_pymatching_auto(decoder: dict[str, Any], circuit: tuple, syndromes: tuple) -> tuple:
    stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, syndrome_info = syndromes
    options = decoder.get("options", {}) or {}
    detection_events = np.asarray(detection_events, dtype=bool)
    observable_flips = as_2d_bool(observable_flips)

    mask = _postselection_mask(detection_events, options)
    events, flips = detection_events[mask], observable_flips[mask]

    mwpm = _mwpm_candidates(stim_circuit, detector_model, events, flips, options)
    candidates = [
        *mwpm,
        *_ensemble_candidates(mwpm, flips, options),
        *_gated_no_correction_candidates(mwpm, events, flips, options),
    ]
    if bool(options.get("include_no_correction", True)):
        candidates.append(_candidate("no_correction", np.zeros_like(flips, dtype=bool), flips))

    best, selection_info = _select_candidate(candidates, options)
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
        **selection_info,
        "candidates": [
            {
                "name": item["name"],
                "ler": float(item["ler"]),
                "uncertainty": float(item["uncertainty"]),
                "logical_failures": int(item["logical_failures"].sum()),
                "shots": int(len(item["logical_failures"])),
                **{key: item[key] for key in _SPLIT_KEYS if key in item},
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


# --- candidates -------------------------------------------------------------------------------


def _candidate(name: str, predicted: np.ndarray, observable_flips: np.ndarray) -> dict[str, Any]:
    failures, ler, sigma = score_predictions(predicted, observable_flips)
    return {
        "name": name,
        "predicted_observables": predicted,
        "logical_failures": failures,
        "ler": ler,
        "uncertainty": sigma,
    }


def _mwpm_candidates(stim_circuit, detector_model, events, flips, options) -> list[dict[str, Any]]:
    """MWPM on the circuit's model and on uniform priors, each optionally also with correlated matching."""
    correlated = bool(options.get("include_correlated_matching", False))
    models = [("calibrated_or_configured", detector_model)]
    models += [
        (f"uniform_p={float(p):g}", detector_model_with_uniform_noise(stim_circuit, float(p)))
        for p in options.get("uniform_probabilities", [])
    ]
    candidates = []
    for name, model in models:
        for enable_correlations in (False, True) if correlated else (False,):
            predicted, *_ = decode_detection_events(model, events, flips, enable_correlations=enable_correlations)
            candidates.append(_candidate(f"correlated_{name}" if enable_correlations else name, predicted, flips))
    return candidates


def _ensemble_candidates(
    mwpm: list[dict[str, Any]], flips: np.ndarray, options: dict[str, Any]
) -> list[dict[str, Any]]:
    """Majority vote over several MWPM priors (a cheap analogue of matching ensembles)."""
    if not bool(options.get("include_matching_ensembles", False)) or len(mwpm) < 3:
        return []
    groups = [("ensemble_all_mwpm", mwpm)]
    uniform = [candidate for candidate in mwpm if candidate["name"].startswith("uniform_p=")]
    if len(uniform) >= 3:
        groups.append(("ensemble_uniform_mwpm", uniform))
    return [
        _candidate(name, _majority_vote([c["predicted_observables"] for c in group]), flips) for name, group in groups
    ]


def _majority_vote(predictions: list[np.ndarray]) -> np.ndarray:
    stacked = np.stack([as_2d_bool(prediction) for prediction in predictions])
    votes = stacked.sum(axis=0)
    half = len(predictions) / 2
    majority = votes > half
    if len(predictions) % 2 == 0:
        ties = votes == half
        majority[ties] = stacked[0][ties]
    return majority


def _gated_no_correction_candidates(
    mwpm: list[dict[str, Any]],
    events: np.ndarray,
    flips: np.ndarray,
    options: dict[str, Any],
) -> list[dict[str, Any]]:
    """No correction on low-syndrome shots, MWPM on the rest: tests whether MWPM over-corrects clean shots."""
    weights = events.sum(axis=1)
    candidates = []
    for threshold_name, threshold in _gated_thresholds(weights, options):
        low_syndrome = weights <= threshold
        if not low_syndrome.any() or low_syndrome.all():
            continue
        for candidate in mwpm:
            predicted = np.array(candidate["predicted_observables"], dtype=bool, copy=True)
            predicted[low_syndrome] = False
            candidates.append(_candidate(f"{candidate['name']}|no_correction_for_{threshold_name}", predicted, flips))
    return candidates


def _gated_thresholds(weights: np.ndarray, options: dict[str, Any]) -> list[tuple[str, int]]:
    thresholds = [
        (f"weight_le_{int(np.quantile(weights, float(q)))}_q{float(q):g}", int(np.quantile(weights, float(q))))
        for q in options.get("gated_no_correction_quantiles", [])
    ]
    thresholds += [
        (f"weight_le_{int(value)}", int(value)) for value in options.get("gated_no_correction_max_weights", [])
    ]
    unique, seen = [], set()
    for name, threshold in thresholds:
        if threshold not in seen:
            unique.append((name, threshold))
            seen.add(threshold)
    return unique


def _postselection_mask(detection_events: np.ndarray, options: dict[str, Any]) -> np.ndarray:
    weights = detection_events.sum(axis=1)
    if "postselect_max_syndrome_weight" in options:
        return weights <= int(options["postselect_max_syndrome_weight"])
    if "postselect_weight_quantile" in options:
        return weights <= int(np.quantile(weights, float(options["postselect_weight_quantile"])))
    return np.ones(len(detection_events), dtype=bool)


# --- selection --------------------------------------------------------------------------------

_SPLIT_KEYS = (
    "selection_ler",
    "selection_logical_failures",
    "selection_shots",
    "evaluation_ler",
    "evaluation_logical_failures",
    "evaluation_shots",
)


def _select_candidate(
    candidates: list[dict[str, Any]], options: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = str(options.get("candidate_selection_mode", DEFAULT_SELECTION_MODE)).lower()
    if mode in {"current_batch", "best_on_current_batch"}:
        return _min_by_position(candidates, lambda item: item["ler"]), {
            "candidate_selection": "best_on_current_batch",
            "selection_is_in_sample": True,
        }
    if mode == "kfold":
        return _select_kfold(candidates, options)
    if mode == "holdout":
        return _select_holdout(candidates, options)
    raise ValueError("candidate_selection_mode must be 'current_batch', 'holdout', or 'kfold'")


def _select_holdout(candidates: list[dict[str, Any]], options: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    shots = int(len(candidates[0]["logical_failures"])) if candidates else 0
    if shots < 2:
        return _min_by_position(candidates, lambda item: item["ler"]), {
            "candidate_selection": "holdout_fallback_current_batch",
            "selection_is_in_sample": True,
            "selection_shots": shots,
            "evaluation_shots": 0,
        }
    selection_fraction = float(options.get("selection_fraction", 0.5))
    if not 0.0 < selection_fraction < 1.0:
        raise ValueError("selection_fraction must be between 0 and 1")
    selection_shots = min(max(int(round(shots * selection_fraction)), 1), shots - 1)

    indices = _shuffled_shots(shots, options)
    selection_mask = np.zeros(shots, dtype=bool)
    selection_mask[indices[:selection_shots]] = True
    evaluation_mask = ~selection_mask
    for candidate in candidates:
        candidate.update(_split_scores(candidate, selection_mask, evaluation_mask))

    # Ties are broken by candidate order, never by evaluation LER (that would leak the test split).
    selected = _min_by_position(candidates, lambda item: item["selection_ler"])
    reported = {
        "name": selected["name"],
        "predicted_observables": selected["predicted_observables"][evaluation_mask],
        "logical_failures": selected["logical_failures"][evaluation_mask],
        "ler": float(selected["evaluation_ler"]),
        "uncertainty": uncertainty(float(selected["evaluation_ler"]), int(selected["evaluation_shots"])),
    }
    return reported, {
        "candidate_selection": "holdout",
        "selection_is_in_sample": False,
        "selection_fraction": selection_fraction,
        "selection_shots": int(selection_shots),
        "evaluation_shots": int(evaluation_mask.sum()),
        "selection_seed": int(options.get("selection_seed", 1)),
        "selected_candidate_selection_ler": float(selected["selection_ler"]),
        "selected_candidate_evaluation_ler": float(selected["evaluation_ler"]),
    }


def _select_kfold(candidates: list[dict[str, Any]], options: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    shots = int(len(candidates[0]["logical_failures"])) if candidates else 0
    folds = int(options.get("candidate_selection_folds", 5))
    if folds < 2:
        raise ValueError("candidate_selection_folds must be at least 2")
    if shots < folds:
        return _min_by_position(candidates, lambda item: item["ler"]), {
            "candidate_selection": "kfold_fallback_current_batch",
            "selection_is_in_sample": True,
            "candidate_selection_folds": folds,
        }

    predicted = np.zeros_like(candidates[0]["predicted_observables"], dtype=bool)
    failures = np.zeros(shots, dtype=bool)
    fold_rows = []
    for fold, evaluation_indices in enumerate(np.array_split(_shuffled_shots(shots, options), folds)):
        evaluation_mask = np.zeros(shots, dtype=bool)
        evaluation_mask[evaluation_indices] = True
        scores = [_split_scores(candidate, ~evaluation_mask, evaluation_mask) for candidate in candidates]
        index = min(range(len(candidates)), key=lambda i: (scores[i]["selection_ler"], i))
        chosen = candidates[index]
        predicted[evaluation_mask] = chosen["predicted_observables"][evaluation_mask]
        failures[evaluation_mask] = chosen["logical_failures"][evaluation_mask]
        fold_rows.append({"fold": fold, "selected_candidate": chosen["name"], **scores[index]})

    ler = _mean(failures)
    reported = {
        "name": "kfold_selected_candidates",
        "predicted_observables": predicted,
        "logical_failures": failures,
        "ler": ler,
        "uncertainty": uncertainty(ler, shots),
    }
    return reported, {
        "candidate_selection": "kfold",
        "selection_is_in_sample": False,
        "candidate_selection_folds": folds,
        "selection_seed": int(options.get("selection_seed", 1)),
        "fold_selected_candidates": fold_rows,
        "unique_selected_candidates": sorted({row["selected_candidate"] for row in fold_rows}),
    }


def _shuffled_shots(shots: int, options: dict[str, Any]) -> np.ndarray:
    indices = np.arange(shots)
    np.random.default_rng(int(options.get("selection_seed", 1))).shuffle(indices)
    return indices


def _split_scores(candidate: dict[str, Any], selection_mask: np.ndarray, evaluation_mask: np.ndarray) -> dict[str, Any]:
    selection = candidate["logical_failures"][selection_mask]
    evaluation = candidate["logical_failures"][evaluation_mask]
    return {
        "selection_ler": _mean(selection),
        "selection_logical_failures": int(selection.sum()),
        "selection_shots": int(selection.size),
        "evaluation_ler": _mean(evaluation),
        "evaluation_logical_failures": int(evaluation.sum()),
        "evaluation_shots": int(evaluation.size),
    }


def _min_by_position(items: list[dict[str, Any]], score) -> dict[str, Any]:
    """Return the lowest-scoring item; ties go to the earliest item (label-free)."""
    return min(enumerate(items), key=lambda pair: (score(pair[1]), pair[0]))[1]


def _mean(values: np.ndarray) -> float:
    return float(values.mean()) if values.size else 0.0
