from __future__ import annotations

from qec_pipeline.config import NoiseConfig
from qec_pipeline.noise.base import NoiseModelSpec


def build_simple_depolarizing_noise(config: NoiseConfig) -> NoiseModelSpec:
    """Build the first simulator baseline noise model.

    Input:
        NoiseConfig with one-qubit, two-qubit, measurement, reset, and idle
        error probabilities.

    Output:
        NoiseModelSpec consumed by code generation and decoder graph creation.
    """
    return NoiseModelSpec(name=config.model, parameters=dict(config.parameters))
