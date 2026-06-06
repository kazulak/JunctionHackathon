from __future__ import annotations

from qec_pipeline.config import MappingConfig
from qec_pipeline.types import CircuitBundle


def apply_emerald_mapping(
    mapping: MappingConfig,
    circuit: CircuitBundle,
) -> CircuitBundle:
    """Map logical/code qubits onto an IQM Emerald hardware patch.

    Input:
        mapping: patch name, origin, orientation, and strategy.
        circuit: CircuitBundle with code coordinates and hardware circuit.

    Output:
        CircuitBundle with initial layout, native-pair diagnostics, SWAP count
        target, and transpilation metadata.
    """
    raise NotImplementedError("Emerald custom mapping")
