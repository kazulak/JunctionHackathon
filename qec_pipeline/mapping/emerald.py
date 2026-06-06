from __future__ import annotations

from typing import Any


def apply_emerald_mapping(
    mapping: dict[str, Any],
    circuit: tuple,
) -> tuple:
    """Map logical/code qubits onto an IQM Emerald hardware patch.

    Input:
        mapping: patch name, origin, orientation, and strategy.
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)

    Output:
        Same circuit tuple, with mapping metadata added later.
    """
    raise NotImplementedError("Emerald custom mapping")
