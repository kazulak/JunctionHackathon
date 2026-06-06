from __future__ import annotations

from typing import Protocol

from qec_pipeline.config import MappingConfig
from qec_pipeline.types import CircuitBundle


class HardwareMapper(Protocol):
    """Interface implemented by IQM Emerald/Garnet patch mappers."""

    def apply_mapping(self, mapping: MappingConfig, circuit: CircuitBundle) -> CircuitBundle:
        """Return CircuitBundle with layout and mapping diagnostics."""
