from __future__ import annotations

from typing import Any, Callable

from qec_pipeline.decoders.gnn_decoder import decode_with_gnn
from qec_pipeline.decoders.ising_decoder import decode_with_ising
from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.decoders.pymatching_calibrated_decoder import decode_with_calibrated_pymatching
from qec_pipeline.decoders.pymatching_decoder import decode_with_pymatching


Decoder = Callable[[dict[str, Any], tuple, tuple], tuple]


DECODERS: dict[str, Decoder] = {
    "observable_rate": decode_observable_rate,
    "pymatching": decode_with_pymatching,
    "pymatching_calibrated": decode_with_calibrated_pymatching,
    "gnn": decode_with_gnn,
    "ising": decode_with_ising,
}


def get_decoder(name: str) -> Decoder:
    try:
        return DECODERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(DECODERS))
        raise ValueError(f"Unknown decoder: {name}. Available: {available}") from exc
