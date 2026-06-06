from __future__ import annotations

from typing import Any, Callable

from qec_pipeline.codes.color_code import build_color_code_circuit
from qec_pipeline.codes.surface_code import build_surface_code_circuit


CodeBuilder = Callable[[dict[str, Any], dict[str, Any], str], tuple]


CODE_BUILDERS: dict[str, CodeBuilder] = {
    "surface_code": build_surface_code_circuit,
    "color_code": build_color_code_circuit,
}


def get_code_builder(name: str) -> CodeBuilder:
    try:
        return CODE_BUILDERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(CODE_BUILDERS))
        raise ValueError(f"Unknown code family: {name}. Available: {available}") from exc
