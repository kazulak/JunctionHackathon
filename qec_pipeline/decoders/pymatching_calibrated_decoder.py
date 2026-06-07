from __future__ import annotations

from typing import Any

from qec_pipeline.decoders.pymatching_decoder import decode_detection_events


def decode_with_calibrated_pymatching(
    decoder: dict[str, Any],
    circuit: tuple,
    syndromes: tuple,
) -> tuple:
    """Decode with PyMatching using the circuit's calibrated detector model."""
    _stim_circuit, detector_model, _measurement_order, circuit_info = circuit
    detection_events, observable_flips, _syndrome_info = syndromes

    predicted_observables, logical_failures, ler, uncertainty = decode_detection_events(
        detector_model,
        detection_events,
        observable_flips,
    )
    shots = int(len(logical_failures))
    decoder_info = {
        "decoder": decoder["name"],
        "shots": shots,
        "logical_failures": int(logical_failures.sum()),
        "num_observables": int(circuit_info["num_observables"]),
        "note": "MWPM decoder using the calibrated detector model in the circuit tuple.",
        "noise_model": circuit_info.get("noise_model"),
        "implemented_noise_model": circuit_info.get("implemented_noise_model"),
    }
    if "calibration_noise" in circuit_info:
        decoder_info["calibration_noise"] = circuit_info["calibration_noise"]

    return predicted_observables, logical_failures, ler, uncertainty, decoder_info

