from __future__ import annotations

from typing import Protocol

from qec_pipeline.config import BackendConfig
from qec_pipeline.types import CircuitBundle, RawMeasurementBundle


class BackendRunner(Protocol):
    """Interface implemented by simulator and IQM hardware runners."""

    def run(self, backend: BackendConfig, circuit: CircuitBundle) -> RawMeasurementBundle:
        """Execute a circuit and return raw shot data."""
