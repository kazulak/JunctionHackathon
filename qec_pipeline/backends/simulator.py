from __future__ import annotations

from typing import Any


def run_simulator_backend(
    backend: dict[str, Any],
    circuit: tuple,
    mapping: dict[str, Any] | None = None,
) -> tuple:
    """Sample raw measurements from a Stim circuit.

    Input:
        backend: `config["backend"]`
        circuit: tuple from `build_surface_code_circuit`

    Output tuple:
        (measurements, counts, raw_info)
    """
    stim_circuit, _detector_model, measurement_order, circuit_info = circuit
    sampler = stim_circuit.compile_sampler(seed=backend.get("options", {}).get("seed"))
    measurements = sampler.sample(shots=int(backend["shots"]))
    raw_info = {
        "backend": backend["name"],
        "shots": int(backend["shots"]),
        "shape": tuple(measurements.shape),
        "simulator": "stim.Circuit.compile_sampler",
        "noise_model": circuit_info.get("noise_model"),
        "implemented_noise_model": circuit_info.get("implemented_noise_model"),
        "stim_to_dense": circuit_info.get("stim_to_dense"),
        "mapping": circuit_info.get("mapping"),
        "meas_order": list(measurement_order),
    }

    return measurements, None, raw_info
