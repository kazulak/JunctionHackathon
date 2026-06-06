from __future__ import annotations

from typing import Protocol

from qec_pipeline.config import CodeConfig, NoiseConfig
from qec_pipeline.types import CircuitBundle


class CodeFactory(Protocol):
    """Interface implemented by surface-code, color-code, and future generators."""

    def build_circuit(self, code: CodeConfig, noise: NoiseConfig | None) -> CircuitBundle:
        """Return canonical and hardware-ready circuit artifacts."""
