from __future__ import annotations

from qec_pipeline.config import CodeConfig, NoiseConfig
from qec_pipeline.types import CircuitBundle


def build_color_code_circuit(
    code: CodeConfig,
    noise: NoiseConfig | None = None,
) -> CircuitBundle:
    """Build a color-code memory experiment.

    Input:
        code: distance, rounds, memory basis, reset mode.
        noise: optional noise model config.

    Output:
        CircuitBundle with the same contract as surface code.

    Implementation notes:
        This is a research branch. Define stabilizers, detector bookkeeping,
        logical observables, and decoder compatibility before hardware work.
    """
    raise NotImplementedError("color-code circuit generation")
