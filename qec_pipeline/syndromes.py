from __future__ import annotations

from qec_pipeline.types import CircuitResult, RawResult, SyndromeResult


def extract_detection_events(
    circuit: CircuitResult,
    raw: RawResult,
) -> SyndromeResult:
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

    from extract_syndromes import extract_syndromes

    result = extract_syndromes(
        raw_meas=measurements,
        stim_circuit_noisy=stim_circuit,
        print_summary=False,
    )

    syndrome_info = {
        "shots": int(result["num_shots"]),
        "num_detectors": int(result["num_detectors"]),
        "num_observables": int(result["obs_flips"].shape[1]),
        "mean_syndrome_weight": float(result["syndrome_weight_per_shot"].mean()),
        "max_syndrome_weight": int(result["syndrome_weight_per_shot"].max()),
        "detector_firing_rate": result["detector_firing_rate"],
    }

    return result["det_events"], result["obs_flips"], syndrome_info
