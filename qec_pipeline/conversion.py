from __future__ import annotations

from qec_pipeline.types import CircuitBundle


def convert_source_to_hardware_circuit(circuit: CircuitBundle) -> CircuitBundle:
    """Convert the canonical circuit into a backend-ready circuit.

    Input:
        CircuitBundle with source_circuit set. For MVP this is expected to be
        a Stim circuit.

    Output:
        CircuitBundle with hardware_circuit, measurement_order, and conversion
        diagnostics populated.

    Implementation notes:
        For the first MVP, wrap the existing Stim-to-Qiskit converter. Later
        this boundary can support color-code circuits, PulLA, or Ising-specific
        circuit generation.
    """
    raise NotImplementedError("source-to-hardware circuit conversion")
