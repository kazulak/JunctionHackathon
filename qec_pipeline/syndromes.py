from __future__ import annotations


def extract_detection_events(
    circuit: tuple,
    raw: tuple,
) -> tuple:
    """Convert raw measurements into decoder-ready data.

    Input:
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)
        raw: (measurements, counts, raw_info)

    Output tuple:
        (detection_events, observable_flips, syndrome_info)

    GNN starts from `detection_events`.
    """
    stim_circuit, _detector_model, _measurement_order, _circuit_info = circuit
    measurements, _counts, _raw_info = raw

    from qec_pipeline.syndrome_extraction import extract_syndromes

    result = extract_syndromes(
        measurements,
        stim_circuit,
    )

    syndrome_info = {
        "shots": int(result["num_shots"]),
        "num_detectors": int(result["num_detectors"]),
        "num_observables": int(result["obs_flips"].shape[1]),
        "mean_syndrome_weight": float(result["syndrome_weight_per_shot"].mean()),
        "max_syndrome_weight": int(result["syndrome_weight_per_shot"].max()),
        "detector_firing_rate": result["detector_firing_rate"],
        "mean_detector_firing_rate": float(result["detector_firing_rate"].mean()),
        "max_detector_firing_rate": float(result["detector_firing_rate"].max()),
        "observable_flip_rate": result["obs_flips"].mean(axis=0),
    }

    return result["det_events"], result["obs_flips"], syndrome_info
