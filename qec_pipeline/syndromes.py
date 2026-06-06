from __future__ import annotations

from qec_pipeline.types import CircuitBundle, RawMeasurementBundle, SyndromeBundle


def extract_detection_events(
    circuit: CircuitBundle,
    raw_measurements: RawMeasurementBundle,
) -> SyndromeBundle:
    """Convert raw measurements into detector events and observable flips.

    Input:
        circuit: canonical circuit with detector definitions and measurement
        order metadata.
        raw_measurements: shot-by-shot measurement array from simulator or IQM.

    Output:
        SyndromeBundle with detection events, observable flips, syndrome
        weights, and detector firing-rate diagnostics.

    Implementation notes:
        For surface-code MVP, wrap the existing Stim `compile_m2d_converter()`
        path. For color code, this may require custom detector bookkeeping.
    """
    shots = len(raw_measurements.measurements)
    num_detectors = int(circuit.metadata["num_detectors"])
    num_observables = int(circuit.metadata["num_observables"])

    detection_events = [[False for _ in range(num_detectors)] for _ in range(shots)]
    observable_flips = [[False for _ in range(num_observables)] for _ in range(shots)]

    return SyndromeBundle(
        detection_events=detection_events,
        observable_flips=observable_flips,
        metadata={
            "shots": shots,
            "num_detectors": num_detectors,
            "num_observables": num_observables,
            "mean_syndrome_weight": 0.0,
            "mode": "toy_no_noise",
        },
    )
