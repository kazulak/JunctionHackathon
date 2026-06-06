from __future__ import annotations

from typing import Any

import numpy as np
import stim


def build_measurement_diagnostics(
    stim_circuit: stim.Circuit,
    measurements: np.ndarray,
    raw_info: dict[str, Any],
    ideal_shots: int = 2000,
) -> list[dict[str, Any]]:
    """Compare observed measurement rates with an ideal noiseless Stim sample."""
    if not getattr(measurements, "size", 0):
        return []

    ideal_circuit = stim_circuit.without_noise()
    ideal_measurements = ideal_circuit.compile_sampler(seed=1).sample(ideal_shots)
    observed_rates = measurements.mean(axis=0)
    ideal_rates = ideal_measurements.mean(axis=0)

    measurement_order = raw_info.get("meas_order") or list(range(stim_circuit.num_measurements))
    stim_to_hardware = (raw_info.get("mapping") or {}).get("stim_to_hardware", {})

    rows = []
    for index, observed_rate in enumerate(observed_rates):
        stim_qubit = int(measurement_order[index]) if index < len(measurement_order) else None
        hardware_qubit = None
        if stim_qubit is not None:
            hardware_qubit = stim_to_hardware.get(str(stim_qubit))

        ideal_rate = float(ideal_rates[index])
        deterministic_value = _deterministic_value(ideal_rate)
        row = {
            "measurement_index": index,
            "stim_qubit": stim_qubit,
            "hardware_qubit": hardware_qubit,
            "ideal_one_rate": ideal_rate,
            "observed_one_rate": float(observed_rate),
            "deterministic_value": deterministic_value,
        }
        if deterministic_value == 0:
            row["unexpected_rate"] = float(observed_rate)
        elif deterministic_value == 1:
            row["unexpected_rate"] = float(1.0 - observed_rate)
        else:
            row["unexpected_rate"] = float(abs(observed_rate - ideal_rate))
        rows.append(row)

    return rows


def _deterministic_value(ideal_rate: float) -> int | None:
    if ideal_rate <= 0.02:
        return 0
    if ideal_rate >= 0.98:
        return 1
    return None
