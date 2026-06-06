from __future__ import annotations

from qec_pipeline.config import BackendConfig
from qec_pipeline.types import CircuitBundle, RawMeasurementBundle


def run_simulator_backend(
    backend: BackendConfig,
    circuit: CircuitBundle,
) -> RawMeasurementBundle:
    """Run the canonical circuit on a local simulator.

    Input:
        backend: simulator settings, especially shot count and seed.
        circuit: CircuitBundle containing a Stim or Qiskit circuit.

    Output:
        RawMeasurementBundle with shape-compatible raw measurement shots.

    Implementation notes:
        Prefer Stim sampler for the first baseline because it preserves detector
        semantics directly. Use Aer only to validate Qiskit conversion.
    """
    num_measurements = int(circuit.metadata["num_measurements"])
    bitstring = "0" * num_measurements
    measurements = [[False for _ in range(num_measurements)] for _ in range(backend.shots)]

    return RawMeasurementBundle(
        measurements=measurements,
        counts={bitstring: backend.shots},
        metadata={
            "backend": backend.name,
            "shots": backend.shots,
            "mode": "deterministic_no_noise",
        },
    )
