from __future__ import annotations

from qec_pipeline.config import NoiseConfig
from qec_pipeline.noise.base import NoiseModelSpec


def build_calibration_aware_noise(config: NoiseConfig) -> NoiseModelSpec:
    """Build a hardware-calibration-aware noise model.

    Input:
        NoiseConfig plus backend calibration data loaded from IQM Resonance.

    Output:
        NoiseModelSpec with qubit-specific, coupler-specific, readout, reset,
        and idle/decoherence parameters.

    Implementation notes:
        This should use IQM calibration data after the simulator baseline works.
    """
    raise NotImplementedError("calibration-aware noise model")
