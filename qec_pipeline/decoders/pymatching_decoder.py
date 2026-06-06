from __future__ import annotations

from typing import Any

import numpy as np
import pymatching

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
    _stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, _syndrome_info = syndromes

    matching = pymatching.Matching.from_detector_error_model(detector_model)
    predicted_observables = matching.decode_batch(detection_events)

    predicted_observables = _as_2d_bool(predicted_observables)
    observable_flips = _as_2d_bool(observable_flips)

    logical_failures_per_observable = np.logical_xor(predicted_observables, observable_flips)
    logical_failures = logical_failures_per_observable.any(axis=1)

    shots = int(len(logical_failures))
    num_failures = int(logical_failures.sum())
    ler = num_failures / shots if shots else 0.0
    uncertainty = binomial_standard_error(ler, shots) if shots else 0.0
    decoder_info = {
        "decoder": decoder["name"],
        "shots": shots,
        "logical_failures": num_failures,
        "num_observables": int(circuit_info["num_observables"]),
        "note": "MWPM decoder from Stim detector error model.",
    }

    return predicted_observables, logical_failures, ler, uncertainty, decoder_info


def _as_2d_bool(array: object) -> np.ndarray:
    result = np.asarray(array, dtype=bool)
    if result.ndim == 1:
        return result.reshape((-1, 1))
    return result
