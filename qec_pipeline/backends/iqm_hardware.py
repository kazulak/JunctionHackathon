from __future__ import annotations

import os
from typing import Any


def run_iqm_hardware_backend(
    backend: dict[str, Any],
    circuit: tuple,
    mapping: dict[str, Any] | None = None,
) -> tuple:
    """Run a Qiskit circuit on IQM Resonance.

    Input:
        backend: IQM backend name, shots, token/server options.
        circuit: (stim_circuit, detector_model, measurement_order, circuit_info)

    Output:
        (measurements, counts, raw_info)
    """
    # OUR CODE: minimal pipeline wrapper for IQM hardware execution.
    #
    # Pipeline helper used below:
    # - qec_pipeline.measurements.counts_to_measurement_array
    #
    # OUR ADDITION used below:
    # - qec_pipeline.conversion.stim_to_qiskit_minimal
    #   This covers memory-X `RX`/`MX` instructions that the provided converter
    #   does not currently cover.
    #
    # Optional mapping comes from qec_pipeline.mapping and is passed to Qiskit as
    # initial_layout. Qiskit/IQM still handles final routing and transpilation.
    from iqm.qiskit_iqm import IQMProvider
    from qec_pipeline.conversion import stim_to_qiskit_minimal
    from qec_pipeline.mapping import select_mapping_from_config
    from qec_pipeline.measurements import counts_to_measurement_array, virtualize_omitted_repeated_resets
    from qiskit import transpile

    stim_circuit, _detector_model, _measurement_order, circuit_info = circuit
    options = backend.get("options", {})

    omit_initial_resets = bool(options.get("omit_initial_resets", False))
    omit_repeated_resets = bool(options.get("omit_repeated_resets", False))
    qiskit_circuit, stim_to_dense, meas_order = stim_to_qiskit_minimal(
        stim_circuit,
        omit_initial_resets=omit_initial_resets,
        omit_repeated_resets=omit_repeated_resets,
    )
    mapping_info = circuit_info.get("mapping")
    if mapping_info is None:
        mapping_info = select_mapping_from_config(mapping or {}, stim_circuit, stim_to_dense)

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
    transpile_kwargs = {
        "backend": iqm_backend,
        "optimization_level": transpile_optimization_level,
    }
    if mapping_info is not None:
        transpile_kwargs["initial_layout"] = mapping_info["initial_layout"]
    transpiled_circuit = transpile(qiskit_circuit, **transpile_kwargs)

    job = iqm_backend.run(transpiled_circuit, shots=int(backend["shots"]))
    result = job.result()
    counts = result.get_counts()
    physical_measurements = counts_to_measurement_array(
        counts,
        num_measurements=stim_circuit.num_measurements,
        total_shots=int(backend["shots"]),
    )
    measurements = physical_measurements
    if omit_repeated_resets:
        measurements = virtualize_omitted_repeated_resets(
            physical_measurements,
            meas_order,
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
        "omit_initial_resets": omit_initial_resets,
        "omit_repeated_resets": omit_repeated_resets,
        "measurement_record": (
            "virtual_reset_from_no_reset_hardware"
            if omit_repeated_resets
            else "physical_qiskit_clbit_order"
        ),
        "physical_measurement_one_rate": (
            physical_measurements.mean(axis=0).tolist()
            if omit_repeated_resets
            else None
        ),
        "stim_to_dense": stim_to_dense,
        "meas_order": meas_order,
        "mapping": mapping_info,
        "noise_model": circuit_info.get("noise_model"),
        "implemented_noise_model": circuit_info.get("implemented_noise_model"),
        "calibration_noise": circuit_info.get("calibration_noise"),
        "basis": circuit_info["basis"],
        "qiskit_circuit_text": str(qiskit_circuit),
        "transpiled_circuit_text": str(transpiled_circuit),
    }

    return measurements, counts, raw_info
