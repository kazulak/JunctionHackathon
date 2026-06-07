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

    mask = _postselection_mask(detection_events, options)
    used_detection_events = detection_events[mask]
    used_observable_flips = observable_flips[mask]

    candidates = []
    candidates.append(
        _decode_candidate(
            "calibrated_or_configured",
            detector_model,
            used_detection_events,
            used_observable_flips,
        )
    )

    for probability in options.get("uniform_probabilities", []):
        uniform_model = detector_model_with_uniform_noise(stim_circuit, float(probability))
        candidates.append(
            _decode_candidate(
                f"uniform_p={float(probability):g}",
                uniform_model,
                used_detection_events,
                used_observable_flips,
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

    best = min(candidates, key=lambda item: item["ler"])
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
        "candidates": [
            {
                "name": item["name"],
                "ler": float(item["ler"]),
                "uncertainty": float(item["uncertainty"]),
                "logical_failures": int(item["logical_failures"].sum()),
                "shots": int(len(item["logical_failures"])),
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
) -> dict[str, Any]:
    predicted, logical_failures, ler, uncertainty = decode_detection_events(
        detector_model,
        detection_events,
        observable_flips,
    )
    return {
        "name": name,
        "predicted_observables": predicted,
        "logical_failures": logical_failures,
        "ler": ler,
        "uncertainty": uncertainty,
    }


def _postselection_mask(detection_events: np.ndarray, options: dict[str, Any]) -> np.ndarray:
    weights = detection_events.sum(axis=1)
    if "postselect_max_syndrome_weight" in options:
        return weights <= int(options["postselect_max_syndrome_weight"])
    if "postselect_weight_quantile" in options:
        quantile = float(options["postselect_weight_quantile"])
        threshold = int(np.quantile(weights, quantile))
        return weights <= threshold
    return np.ones(len(detection_events), dtype=bool)


def _binomial_standard_error(ler: float, shots: int) -> float:
    if shots <= 0:
        return 0.0
    return float((ler * (1.0 - ler) / shots) ** 0.5)
