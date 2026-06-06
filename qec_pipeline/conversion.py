from __future__ import annotations


def convert_source_to_hardware_circuit(circuit: tuple) -> tuple:
    """Convert the canonical circuit into a backend-ready circuit.

    Input:
        (stim_circuit, detector_model, measurement_order, circuit_info)

    Output:
        Same tuple shape. Hardware conversion will be added later.

    Implementation notes:
        For the first MVP, wrap the existing Stim-to-Qiskit converter. Later
        this boundary can support color-code circuits, PulLA, or Ising-specific
        circuit generation.
    """
    raise NotImplementedError("source-to-hardware circuit conversion")
