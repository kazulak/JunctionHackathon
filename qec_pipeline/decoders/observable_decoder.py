from __future__ import annotations

from typing import Any

import numpy as np

from qec_pipeline.decoders.scoring import decoder_output, score_predictions


def decode_observable_rate(decoder: dict[str, Any], circuit: tuple, syndromes: tuple) -> tuple:
    """No correction: count raw observable flips as logical failures.

    Not a real decoder; a sanity check (no noise must give LER 0) and the
    "uncorrected" reference for every other decoder.
    """
    circuit_info = circuit[3]
    _detection_events, observable_flips, _syndrome_info = syndromes
    predicted = np.zeros((len(observable_flips), int(circuit_info["num_observables"])), dtype=bool)
    failures, ler, _uncertainty = score_predictions(predicted, observable_flips)
    return decoder_output(
        decoder, circuit_info, predicted, failures, ler, "No correction applied; observable flips are counted directly."
    )
