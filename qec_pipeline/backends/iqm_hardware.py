from __future__ import annotations

from typing import Any

from qec_pipeline.types import CircuitResult, RawResult


def run_iqm_hardware_backend(
    backend: dict[str, Any],
    circuit: CircuitResult,
) -> RawResult:
    """Run a Qiskit circuit on IQM Resonance.

    Input:
        backend: IQM backend name, shots, token/server options.
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)

    Output:
        (measurements, counts, raw_info)
    """
    raise NotImplementedError("IQM hardware backend")
