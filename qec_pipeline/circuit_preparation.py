from __future__ import annotations

from typing import Any

from qec_pipeline.mapping import active_stim_to_dense, select_mapping_from_config
from qec_pipeline.noise.iqm_calibration import apply_iqm_calibration_noise


def prepare_circuit_for_execution(config: dict[str, Any], circuit: tuple) -> tuple:
    """Attach mapping metadata and optional calibrated IQM noise before execution."""
    circuit = _attach_mapping(config["mapping"], circuit)

    if config["noise"].get("model") == "iqm_calibration":
        circuit = apply_iqm_calibration_noise(circuit, config["noise"], config["mapping"])

    return circuit


def _attach_mapping(mapping: dict[str, Any], circuit: tuple) -> tuple:
    stim_circuit, detector_model, measurement_order, circuit_info = circuit
    strategy = mapping.get("strategy", "none")
    if strategy in {"none", None}:
        return circuit

    stim_to_dense = active_stim_to_dense(stim_circuit)
    mapping_info = select_mapping_from_config(mapping, stim_circuit, stim_to_dense)
    if mapping_info is None:
        return circuit

    info = dict(circuit_info)
    info["stim_to_dense"] = stim_to_dense
    info["mapping"] = mapping_info
    info["mapping_strategy"] = mapping_info.get("strategy", strategy)
    info["mapping_score"] = mapping_info.get("score")

    return stim_circuit, detector_model, measurement_order, info
