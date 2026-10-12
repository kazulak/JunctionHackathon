from __future__ import annotations

from typing import Any

import numpy as np
import pymatching
import stim

from qec_pipeline.decoders.scoring import as_2d_bool, decoder_output, score_predictions


def decode_with_pymatching(decoder: dict[str, Any], circuit: tuple, syndromes: tuple) -> tuple:
    """Minimum-weight perfect matching (PyMatching) on the circuit's detector error model.

    Registered as `pymatching` and `pymatching_calibrated`: with `noise.model: iqm_calibration`
    the circuit's detector error model already carries the per-qubit calibration noise.

    Options:
        enable_correlations: correlated matching (uses hyperedges of the error model).
        noise_sweep_probabilities: also decode with uniform-noise models, for comparison.
    """
    stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, _syndrome_info = syndromes
    options = decoder.get("options", {}) or {}
    correlated = bool(options.get("enable_correlations", False))

    predicted, failures, ler, _uncertainty = decode_detection_events(
        detector_model, detection_events, observable_flips, enable_correlations=correlated
    )
    info: dict[str, Any] = {
        "enable_correlations": correlated,
        "noise_model": circuit_info.get("noise_model"),
        "implemented_noise_model": circuit_info.get("implemented_noise_model"),
    }
    if "calibration_noise" in circuit_info:
        info["calibration_noise"] = circuit_info["calibration_noise"]
    probabilities = options.get("noise_sweep_probabilities", [])
    if probabilities:
        info["noise_sweep"] = pymatching_noise_sweep(stim_circuit, detection_events, observable_flips, probabilities)
    return decoder_output(
        decoder, circuit_info, predicted, failures, ler, "MWPM decoder from the circuit's detector error model.", **info
    )


def decode_detection_events(
    detector_model: stim.DetectorErrorModel,
    detection_events: np.ndarray,
    observable_flips: np.ndarray,
    enable_correlations: bool = False,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Decode one batch with a supplied detector error model: (predicted, failures, ler, uncertainty)."""
    matching = pymatching.Matching.from_detector_error_model(detector_model, enable_correlations=enable_correlations)
    predicted = as_2d_bool(matching.decode_batch(detection_events, enable_correlations=enable_correlations))
    return predicted, *score_predictions(predicted, observable_flips)


def pymatching_noise_sweep(
    stim_circuit: stim.Circuit,
    detection_events: np.ndarray,
    observable_flips: np.ndarray,
    probabilities: list[float],
) -> list[dict[str, float | int]]:
    """Decode with uniform noise models of several strengths."""
    rows = []
    for probability in probabilities:
        detector_model = detector_model_with_uniform_noise(stim_circuit, float(probability))
        _predicted, failures, ler, uncertainty = decode_detection_events(
            detector_model, detection_events, observable_flips
        )
        rows.append(
            {
                "probability": float(probability),
                "ler": float(ler),
                "uncertainty": float(uncertainty),
                "logical_failures": int(failures.sum()),
                "shots": int(len(failures)),
            }
        )
    return rows


def detector_model_with_uniform_noise(stim_circuit: stim.Circuit, probability: float) -> stim.DetectorErrorModel:
    """Detector error model after setting every one-parameter noise channel to `probability`."""
    rewritten = stim.Circuit()
    for instruction in stim_circuit.flattened():
        args = instruction.gate_args_copy()
        if instruction.name in _SINGLE_PROBABILITY_NOISE and args:
            args = [float(probability)]
        rewritten.append(instruction.name, instruction.targets_copy(), args)
    return rewritten.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)


_SINGLE_PROBABILITY_NOISE = frozenset({"X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"})
