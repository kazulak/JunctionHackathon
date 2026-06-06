from __future__ import annotations

import os
from typing import Any


def run_iqm_hardware_backend(
    backend: dict[str, Any],
    circuit: tuple,
) -> tuple:
    """Run a Qiskit circuit on IQM Resonance.

    Input:
        backend: IQM backend name, shots, token/server options.
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)

    Output:
        (measurements, counts, raw_info)
    """
    # OUR CODE: minimal pipeline wrapper around the challenge-provided helpers.
    #
    # PROVIDED helper used below:
    # - internal_helpers.counts_to_measurement_array
    #
    # OUR ADDITION used below:
    # - qec_pipeline.conversion.stim_to_qiskit_minimal
    #   This covers memory-X `RX`/`MX` instructions that the provided converter
    #   does not currently cover.
    #
    # This intentionally does not implement custom mapping yet. It lets Qiskit/IQM
    # transpilation produce the first hardware baseline.
    from internal_helpers import counts_to_measurement_array
    from iqm.qiskit_iqm import IQMProvider
    from qec_pipeline.conversion import stim_to_qiskit_minimal
    from qiskit import transpile

    stim_circuit, _detector_model, _measurement_order, circuit_info = circuit
    options = backend.get("options", {})

    qiskit_circuit, stim_to_dense, meas_order = stim_to_qiskit_minimal(stim_circuit)

    provider_args = {
        "quantum_computer": options.get(
            "quantum_computer",
            os.environ.get("IQM_QUANTUM_COMPUTER", "emerald"),
        )
    }
    if "token" in options:
        # OUR CODE: only pass token when it is explicitly in YAML.
        # If IQM_TOKEN is set in the shell/.env, IQM's client reads it itself.
        # Passing the env token here as an argument causes a mixed-auth-source error.
        provider_args["token"] = options["token"]

    provider = IQMProvider(
        options.get("server_url", os.environ.get("IQM_SERVER_URL", "https://resonance.meetiqm.com")),
        **provider_args,
    )
    iqm_backend = provider.get_backend()

    transpile_optimization_level = int(options.get("optimization_level", 3))
    transpiled_circuit = transpile(
        qiskit_circuit,
        iqm_backend,
        optimization_level=transpile_optimization_level,
    )

    job = iqm_backend.run(transpiled_circuit, shots=int(backend["shots"]))
    result = job.result()
    counts = result.get_counts()
    measurements = counts_to_measurement_array(
        counts,
        num_measurements=stim_circuit.num_measurements,
        total_shots=int(backend["shots"]),
    )

    raw_info = {
        "backend": backend["name"],
        "quantum_computer": options.get("quantum_computer", "emerald"),
        "shots": int(backend["shots"]),
        "job_id": job.job_id(),
        "qiskit_depth": qiskit_circuit.depth(),
        "transpiled_depth": transpiled_circuit.depth(),
        "qiskit_ops": dict(qiskit_circuit.count_ops()),
        "transpiled_ops": dict(transpiled_circuit.count_ops()),
        "stim_to_dense": stim_to_dense,
        "meas_order": meas_order,
        "basis": circuit_info["basis"],
        "qiskit_circuit_text": str(qiskit_circuit),
        "transpiled_circuit_text": str(transpiled_circuit),
    }

    return measurements, counts, raw_info
