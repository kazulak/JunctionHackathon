from __future__ import annotations

from typing import Any

import numpy as np
import pymatching
import stim

from qec_pipeline.analysis.metrics import binomial_standard_error


def decode_with_pymatching(
    decoder: dict[str, Any],
    circuit: tuple,
    syndromes: tuple,
) -> tuple:
    """Decode detector events with PyMatching/MWPM.

    Input:
        decoder: PyMatching options.
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)
        syndromes: detection events and observed logical flips.

    Output:
        (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
    """
    stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, _syndrome_info = syndromes

    predicted_observables, logical_failures, ler, uncertainty = decode_detection_events(
        detector_model,
        detection_events,
        observable_flips,
    )
    shots = int(len(logical_failures))
    num_failures = int(logical_failures.sum())
    decoder_info = {
        "decoder": decoder["name"],
        "shots": shots,
        "logical_failures": num_failures,
        "num_observables": int(circuit_info["num_observables"]),
        "note": "MWPM decoder from Stim detector error model.",
    }
    probabilities = decoder.get("options", {}).get("noise_sweep_probabilities", [])
    if probabilities:
        decoder_info["noise_sweep"] = pymatching_noise_sweep(
            stim_circuit,
            detection_events,
            observable_flips,
            probabilities,
        )

    return predicted_observables, logical_failures, ler, uncertainty, decoder_info


def decode_detection_events(
    detector_model: stim.DetectorErrorModel,
    detection_events: np.ndarray,
    observable_flips: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Decode one batch with a supplied detector error model."""
    matching = pymatching.Matching.from_detector_error_model(detector_model)
    predicted_observables = _as_2d_bool(matching.decode_batch(detection_events))
    observable_flips = _as_2d_bool(observable_flips)

    logical_failures_per_observable = np.logical_xor(predicted_observables, observable_flips)
    logical_failures = logical_failures_per_observable.any(axis=1)

    shots = int(len(logical_failures))
    ler = float(logical_failures.mean()) if shots else 0.0
    uncertainty = binomial_standard_error(ler, shots) if shots else 0.0
    return predicted_observables, logical_failures, ler, uncertainty


def pymatching_noise_sweep(
    stim_circuit: stim.Circuit,
    detection_events: np.ndarray,
    observable_flips: np.ndarray,
    probabilities: list[float],
) -> list[dict[str, float | int]]:
    """Try several uniform Stim noise probabilities with PyMatching."""
    rows = []
    for probability in probabilities:
        detector_model = detector_model_with_uniform_noise(stim_circuit, float(probability))
        _predicted, logical_failures, ler, uncertainty = decode_detection_events(
            detector_model,
            detection_events,
            observable_flips,
        )
        rows.append(
            {
                "probability": float(probability),
                "ler": float(ler),
                "uncertainty": float(uncertainty),
                "logical_failures": int(logical_failures.sum()),
                "shots": int(len(logical_failures)),
            }
        )
    return rows


def detector_model_with_uniform_noise(
    stim_circuit: stim.Circuit,
    probability: float,
) -> stim.DetectorErrorModel:
    """Build a DEM after replacing simple one-argument noise rates."""
    rewritten = stim.Circuit()
    for instruction in stim_circuit.flattened():
        args = instruction.gate_args_copy()
        if instruction.name in _SINGLE_PROBABILITY_NOISE and args:
            args = [float(probability)]
        rewritten.append(instruction.name, instruction.targets_copy(), args)
    return rewritten.detector_error_model(decompose_errors=True)


def _as_2d_bool(array: object) -> np.ndarray:
    result = np.asarray(array, dtype=bool)
    if result.ndim == 1:
        return result.reshape((-1, 1))
    return result


_SINGLE_PROBABILITY_NOISE = frozenset(
    {
        "X_ERROR",
        "Y_ERROR",
        "Z_ERROR",
        "DEPOLARIZE1",
        "DEPOLARIZE2",
    }
)
