from __future__ import annotations

from qec_pipeline.config import DecoderConfig
from qec_pipeline.types import CircuitBundle, DecoderResult, SyndromeBundle


def decode_with_ising(
    decoder: DecoderConfig,
    circuit: CircuitBundle,
    syndromes: SyndromeBundle,
) -> DecoderResult:
    """Decode or predecode via NVIDIA Ising tooling.

    Input:
        decoder: Ising/predecoder options.
        circuit: compatible circuit and detector metadata.
        syndromes: detection events and observed logical flips.

    Output:
        DecoderResult compatible with PyMatching/GNN comparison.

    Implementation notes:
        This likely needs a separate circuit-generation path around the Ising
        MemoryCircuit abstraction, then adaptation into our common interface.
    """
    raise NotImplementedError("NVIDIA Ising decoder")
