from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from qec_pipeline.config import NoiseConfig


@dataclass(frozen=True)
class NoiseModelSpec:
    """Framework-neutral noise-model description."""

    name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    calibration_snapshot: dict[str, Any] | None = None


class NoiseModelBuilder(Protocol):
    def build(self, config: NoiseConfig) -> NoiseModelSpec:
        """Build a noise model from config."""
