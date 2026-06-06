from __future__ import annotations

from typing import Any

from qec_pipeline.analysis.metrics import binomial_standard_error


def decode_observable_rate(
    decoder: dict[str, Any],
    circuit: tuple,
    syndromes: tuple,
) -> tuple:
    """Use observable flips as logical failures.

    This is not a real decoder. It is the first sanity check:
    no noise should give no observable flips and LER 0.

    Input:
        decoder: `config["decoder"]`
        circuit: circuit tuple
        syndromes: (detection_events, observable_flips, syndrome_info)

    Output tuple:
        (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
    """
    _stim_circuit, _detector_model, _measurement_order, circuit_info = circuit
    _detection_events, observable_flips, _syndrome_info = syndromes

    shots = len(observable_flips)
    num_observables = int(circuit_info["num_observables"])
    predicted_observables = [[False for _ in range(num_observables)] for _ in range(shots)]
    logical_failures = _logical_failures_from_observables(observable_flips)
    num_failures = sum(logical_failures)
    ler = num_failures / shots if shots else 0.0
    uncertainty = binomial_standard_error(ler, shots) if shots else 0.0
    decoder_info = {
        "decoder": decoder["name"],
        "shots": shots,
        "logical_failures": num_failures,
        "note": "No correction applied; observable flips are counted directly.",
    }

    return predicted_observables, logical_failures, ler, uncertainty, decoder_info


def _logical_failures_from_observables(observable_flips: object) -> list[bool]:
    if hasattr(observable_flips, "any"):
        return [bool(value) for value in observable_flips.any(axis=1)]
    return [any(bool(value) for value in row) for row in observable_flips]
