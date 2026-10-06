from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.decoders.pymatching_auto_decoder import decode_with_pymatching_auto
from qec_pipeline.decoders.pymatching_calibrated_decoder import decode_with_calibrated_pymatching
from qec_pipeline.decoders.pymatching_decoder import decode_with_pymatching
from qec_pipeline.decoders.pymatching_pij_decoder import decode_with_pymatching_pij

Decoder = Callable[[dict[str, Any], tuple, tuple], tuple]


DECODERS: dict[str, Decoder] = {
    "observable_rate": decode_observable_rate,
    "pymatching": decode_with_pymatching,
    "pymatching_calibrated": decode_with_calibrated_pymatching,
    "pymatching_auto": decode_with_pymatching_auto,
    "pymatching_pij": decode_with_pymatching_pij,
}


def get_decoder(name: str) -> Decoder:
    try:
        return DECODERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(DECODERS))
        raise ValueError(f"Unknown decoder: {name}. Available: {available}") from exc
