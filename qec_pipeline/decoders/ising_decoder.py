from __future__ import annotations

from typing import Any

from qec_pipeline.types import CircuitResult, DecodeResult, SyndromeResult


def decode_with_ising(
    decoder: dict[str, Any],
    circuit: CircuitResult,
    syndromes: SyndromeResult,
) -> DecodeResult:
    """Decode or predecode via NVIDIA Ising tooling.

    Input:
        decoder: Ising/predecoder options.
        circuit: compatible circuit and detector metadata.
        syndromes: detection events and observed logical flips.

    Output:
        (predicted_observables, logical_failures, ler, uncertainty, decoder_info)

    Implementation notes:
        This likely needs a separate circuit-generation path around the Ising
        MemoryCircuit abstraction, then adaptation into our common interface.
    """
    raise NotImplementedError("NVIDIA Ising decoder")
