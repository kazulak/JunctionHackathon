from __future__ import annotations

from qec_pipeline.config import DecoderConfig
from qec_pipeline.types import CircuitBundle, DecoderResult, SyndromeBundle


def decode_with_pymatching(
    decoder: DecoderConfig,
    circuit: CircuitBundle,
    syndromes: SyndromeBundle,
) -> DecoderResult:
    """Decode detector events with PyMatching/MWPM.

    Input:
        decoder: PyMatching options.
        circuit: CircuitBundle with detector_model.
        syndromes: detection events and observed logical flips.

    Output:
        DecoderResult with predicted logical corrections, logical failures,
        LER, uncertainty, and decoder metadata.
    """
    raise NotImplementedError("PyMatching decoder")
