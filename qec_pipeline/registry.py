from __future__ import annotations

from typing import Callable

from qec_pipeline.config import ExperimentConfig
from qec_pipeline.types import PipelineState

StageFactory = Callable[[ExperimentConfig], Callable[[PipelineState], PipelineState]]


def select_code_family(name: str) -> str:
    """Validate and normalize code-family selection from config."""
    allowed = {"surface_code", "color_code"}
    if name not in allowed:
        raise ValueError(f"Unsupported code family '{name}'. Allowed: {sorted(allowed)}")
    return name


def select_decoder(name: str) -> str:
    """Validate and normalize decoder selection from config."""
    allowed = {"trivial", "pymatching", "gnn", "ising"}
    if name not in allowed:
        raise ValueError(f"Unsupported decoder '{name}'. Allowed: {sorted(allowed)}")
    return name


def select_backend(name: str) -> str:
    """Validate and normalize backend selection from config."""
    allowed = {"simulator", "iqm_hardware"}
    if name not in allowed:
        raise ValueError(f"Unsupported backend '{name}'. Allowed: {sorted(allowed)}")
    return name
