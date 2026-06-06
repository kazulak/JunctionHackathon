from __future__ import annotations

from typing import Any


def build_color_code_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    """Build a color-code memory experiment.

    Input:
        code: `config["code"]`
        noise: `config["noise"]`
        basis: "memory_z" or "memory_x"

    Output:
        (stim_circuit, detector_model, measurement_order, circuit_info)

    Implementation notes:
        This is a research branch. Define stabilizers, detector bookkeeping,
        logical observables, and decoder compatibility before hardware work.
    """
    raise NotImplementedError("color-code circuit generation")
