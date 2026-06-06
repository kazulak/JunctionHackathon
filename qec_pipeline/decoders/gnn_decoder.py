from __future__ import annotations

from qec_pipeline.config import DecoderConfig
from qec_pipeline.types import CircuitBundle, DecoderResult, SyndromeBundle


def train_gnn_decoder(
    decoder: DecoderConfig,
    circuit: CircuitBundle,
    training_syndromes: SyndromeBundle,
) -> object:
    """Train a GNN decoder candidate.

    Input:
        decoder: architecture, optimizer, and training settings.
        circuit: detector graph and code geometry.
        training_syndromes: simulated or historical labeled syndrome data.

    Output:
        Trained model object or path to saved model artifact.

    Implementation notes:
        This should be a separate experiment path. Keep inference compatible
        with the same DecoderResult interface as PyMatching.
    """
    raise NotImplementedError("GNN decoder training")


def decode_with_gnn(
    decoder: DecoderConfig,
    circuit: CircuitBundle,
    syndromes: SyndromeBundle,
) -> DecoderResult:
    """Decode detector events using a trained GNN.

    Input:
        decoder: model checkpoint and inference options.
        circuit: detector graph and geometry features.
        syndromes: detection events and observed logical flips.

    Output:
        DecoderResult with the same contract as other decoders.
    """
    raise NotImplementedError("GNN decoder inference")
