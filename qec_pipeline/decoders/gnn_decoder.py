from __future__ import annotations

from typing import Any


def train_gnn_decoder(
    decoder: dict[str, Any],
    circuit: tuple,
    training_syndromes: tuple,
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
        with the same tuple output as the other decoders.
    """
    raise NotImplementedError("GNN decoder training")


def decode_with_gnn(
    decoder: dict[str, Any],
    circuit: tuple,
    syndromes: tuple,
) -> tuple:
    """Decode detector events using a trained GNN.

    Input:
        decoder: model checkpoint and inference options.
        circuit: detector graph and geometry features.
        syndromes: detection events and observed logical flips.

    Output:
        (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
    """
    raise NotImplementedError("GNN decoder inference")
