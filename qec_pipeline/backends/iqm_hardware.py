from __future__ import annotations

from qec_pipeline.config import BackendConfig
from qec_pipeline.types import CircuitBundle, RawMeasurementBundle


def run_iqm_hardware_backend(
    backend: BackendConfig,
    circuit: CircuitBundle,
) -> RawMeasurementBundle:
    """Run a Qiskit circuit on IQM Resonance.

    Input:
        backend: IQM backend name, shots, token/server options.
        circuit: CircuitBundle with hardware_circuit and measurement order.

    Output:
        RawMeasurementBundle with expanded raw measurements, counts, job ID,
        transpilation metrics, backend name, and calibration snapshot if used.
    """
    raise NotImplementedError("IQM hardware backend")
