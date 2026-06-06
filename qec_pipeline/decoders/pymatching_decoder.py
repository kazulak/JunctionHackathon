from __future__ import annotations

from typing import Any

from qec_pipeline.types import CircuitResult, DecodeResult, SyndromeResult


def decode_with_pymatching(
    decoder: dict[str, Any],
    circuit: CircuitResult,
    syndromes: SyndromeResult,
) -> DecodeResult:
    """Decode detector events with PyMatching/MWPM.

    Input:
        decoder: PyMatching options.
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)
        syndromes: detection events and observed logical flips.

    Output:
        (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
    """
    raise NotImplementedError("PyMatching decoder")
