from __future__ import annotations

from qec_pipeline.config import DecoderConfig
from qec_pipeline.types import CircuitBundle, DecoderResult, SyndromeBundle


def decode_trivial_no_noise(
    decoder: DecoderConfig,
    circuit: CircuitBundle,
    syndromes: SyndromeBundle,
) -> DecoderResult:
    """Decode the toy no-noise demo.

    Input:
        decoder: expected to be `trivial`.
        circuit: toy circuit metadata.
        syndromes: zero detector events and zero observable flips.

    Output:
        DecoderResult with no predicted corrections and LER equal to 0.
    """
    shots = len(syndromes.observable_flips)
    num_observables = int(circuit.metadata["num_observables"])
    predicted = [[False for _ in range(num_observables)] for _ in range(shots)]
    logical_failures = [False for _ in range(shots)]

    return DecoderResult(
        predicted_observables=predicted,
        logical_failures=logical_failures,
        ler=0.0,
        uncertainty=0.0,
        metadata={
            "decoder": decoder.name,
            "shots": shots,
            "logical_failures": 0,
            "mode": "toy_no_noise",
        },
    )
