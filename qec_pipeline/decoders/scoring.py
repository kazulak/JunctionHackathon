"""Turning predicted observables into logical failures, shared by all decoders."""

from __future__ import annotations

from typing import Any

import numpy as np

from qec_pipeline.analysis.metrics import binomial_standard_error


def as_2d_bool(array: object) -> np.ndarray:
    """Boolean (shots, observables) array; a 1-D input is one observable."""
    result = np.asarray(array, dtype=bool)
    return result.reshape((-1, 1)) if result.ndim == 1 else result


def uncertainty(ler: float, shots: int) -> float:
    """Binomial 1-sigma of an LER, 0 for an empty batch."""
    return binomial_standard_error(ler, shots) if shots > 0 else 0.0


def score_predictions(predicted: object, observable_flips: object) -> tuple[np.ndarray, float, float]:
    """Per-shot logical failures (any observable predicted wrongly), LER, and its 1-sigma."""
    failures = np.logical_xor(as_2d_bool(predicted), as_2d_bool(observable_flips)).any(axis=1)
    shots = int(len(failures))
    ler = float(failures.mean()) if shots else 0.0
    return failures, ler, uncertainty(ler, shots)


def decoder_output(
    decoder: dict[str, Any],
    circuit_info: dict[str, Any],
    predicted: np.ndarray,
    failures: np.ndarray,
    ler: float,
    note: str,
    **info: Any,
) -> tuple:
    """The standard decoder return tuple: (predicted, failures, ler, uncertainty, decoder_info)."""
    shots = int(len(failures))
    decoder_info = {
        "decoder": decoder["name"],
        "shots": shots,
        "logical_failures": int(np.sum(failures)),
        "num_observables": int(circuit_info["num_observables"]),
        "note": note,
        **info,
    }
    return predicted, failures, ler, uncertainty(ler, shots), decoder_info
