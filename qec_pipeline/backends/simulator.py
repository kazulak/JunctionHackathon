from __future__ import annotations

from typing import Any

from qec_pipeline.types import CircuitResult, RawResult


def run_simulator_backend(
    backend: dict[str, Any],
    circuit: CircuitResult,
) -> RawResult:
    """Sample raw measurements from a Stim circuit.

    Input:
        backend: `config["backend"]`
        circuit: tuple from `build_surface_code_circuit`

    Output tuple:
        (measurements, counts, raw_info)
    """
    stim_circuit, _detector_model, _measurement_order, _circuit_info = circuit
    sampler = stim_circuit.compile_sampler(seed=backend.get("options", {}).get("seed"))
    measurements = sampler.sample(shots=int(backend["shots"]))
    raw_info = {
        "backend": backend["name"],
        "shots": int(backend["shots"]),
        "shape": tuple(measurements.shape),
        "simulator": "stim.Circuit.compile_sampler",
    }

    return measurements, None, raw_info
