from __future__ import annotations

from typing import Protocol

from qec_pipeline.config import DecoderConfig
from qec_pipeline.types import CircuitBundle, DecoderResult, SyndromeBundle


class Decoder(Protocol):
    """Interface implemented by PyMatching, GNN, Ising, and future decoders."""

    def decode(
        self,
        decoder: DecoderConfig,
        circuit: CircuitBundle,
        syndromes: SyndromeBundle,
    ) -> DecoderResult:
        """Return predictions, logical failures, LER, and uncertainty."""
