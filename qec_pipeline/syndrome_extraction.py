from __future__ import annotations

import numpy as np
import stim


def extract_syndromes(
    raw_meas: np.ndarray,
    stim_circuit: stim.Circuit,
) -> dict:
    """Convert raw measurements into detector events and observable flips."""
    converter = stim_circuit.compile_m2d_converter()
    det_events, obs_flips = converter.convert(
        measurements=raw_meas.astype(bool),
        separate_observables=True,
    )

    syndrome_weight_per_shot = det_events.sum(axis=1).astype(int)
    detector_firing_rate = det_events.mean(axis=0)

    return {
        "det_events": det_events,
        "obs_flips": obs_flips,
        "raw_meas": raw_meas,
        "num_detectors": int(det_events.shape[1]),
        "num_shots": int(len(raw_meas)),
        "syndrome_weight_per_shot": syndrome_weight_per_shot,
        "detector_firing_rate": detector_firing_rate,
    }
