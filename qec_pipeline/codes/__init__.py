from __future__ import annotations

from collections.abc import Callable
from typing import Any

from qec_pipeline.codes.surface_code import (
    build_iqm_surface_code_circuit,
    build_surface_code_circuit,
    build_unrotated_surface_code_circuit,
)

CodeBuilder = Callable[[dict[str, Any], dict[str, Any], str], tuple]


CODE_BUILDERS: dict[str, CodeBuilder] = {
    "surface_code": build_surface_code_circuit,
    "surface_code_iqm": build_iqm_surface_code_circuit,
    "surface_code_unrotated": build_unrotated_surface_code_circuit,
}


def get_code_builder(name: str) -> CodeBuilder:
    try:
        return CODE_BUILDERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(CODE_BUILDERS))
        raise ValueError(f"Unknown code family: {name}. Available: {available}") from exc


def build_code_circuit(code: dict[str, Any], noise: dict[str, Any], basis: str) -> tuple:
    """Build the circuit of `code.family` (default `surface_code`) for one basis."""
    return get_code_builder(code.get("family", "surface_code"))(code, noise, basis)
