from __future__ import annotations

from typing import Any

from qec_pipeline.codes.surface_code import build_surface_code_circuit


def build_iqm_surface_code_circuit(
    code: dict[str, Any],
    noise: dict[str, Any],
    basis: str,
) -> tuple:
    """Build a rotated surface-code circuit for calibration-aware IQM work.

    This builder intentionally starts from a clean Stim circuit. If
    `noise.model: iqm_calibration` is selected, the pipeline injects per-qubit
    and per-coupler calibration noise after hardware mapping is selected.
    """
    base_code = dict(code)
    base_code["family"] = "surface_code"
    clean_noise = {"model": "no_noise", "parameters": {}}

    stim_circuit, detector_model, measurement_order, circuit_info = build_surface_code_circuit(
        base_code,
        clean_noise,
        basis,
    )

    info = dict(circuit_info)
    info["code_family"] = "surface_code_iqm"
    info["surface_code_variant"] = "rotated_iqm_calibration_first"
    info["noise_model"] = noise.get("model", "no_noise")
    info["noise_parameters"] = dict(noise.get("parameters", {}))
    info["stim_noise_kwargs"] = {}

    return stim_circuit, detector_model, measurement_order, info

