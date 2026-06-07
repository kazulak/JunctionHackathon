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
    return run_iqm_hardware_batch_backend(
        backend,
        [{"circuit": circuit, "mapping": mapping}],
    )[0]


def run_iqm_hardware_batch_backend(
    backend: dict[str, Any],
    requests: list[dict[str, Any]],
) -> list[tuple]:
    """Submit several IQM circuits in one batch job and return raw tuples."""
    from iqm.qiskit_iqm import IQMProvider
    from qiskit import transpile

    options = backend.get("options", {})
    provider = IQMProvider(
        options.get("server_url", os.environ.get("IQM_SERVER_URL", "https://resonance.meetiqm.com")),
        **_provider_args(options),
    )
    iqm_backend = provider.get_backend()

    prepared = [
        _prepare_iqm_request(backend, request["circuit"], request.get("mapping"), iqm_backend)
        for request in requests
    ]
    transpiled_circuits = [item["transpiled_circuit"] for item in prepared]
    job = iqm_backend.run(transpiled_circuits, shots=int(backend["shots"]))
    result = job.result()
    batch_size = len(prepared)

    raws = []
    for index, item in enumerate(prepared):
        counts = result.get_counts() if batch_size == 1 else result.get_counts(index)
        raws.append(_raw_tuple_from_counts(backend, item, counts, job, index, batch_size))
    return raws


def _prepare_iqm_request(
    backend: dict[str, Any],
    circuit: tuple,
    mapping: dict[str, Any] | None,
    iqm_backend: Any,
) -> dict[str, Any]:
    from qec_pipeline.conversion import stim_to_qiskit_minimal
    from qec_pipeline.mapping import select_mapping_from_config
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

    transpile_optimization_level = int(options.get("optimization_level", 3))
    transpile_kwargs = {
        "backend": iqm_backend,
        "optimization_level": transpile_optimization_level,
    }
    transpile_kwargs.update(_optional_transpile_kwargs(options))
    if mapping_info is not None:
        transpile_kwargs["initial_layout"] = mapping_info["initial_layout"]
    transpiled_circuit = transpile(qiskit_circuit, **transpile_kwargs)
    transpiled_circuit, dd_info = _maybe_apply_dynamical_decoupling(
        transpiled_circuit,
        iqm_backend,
        options,
    )

    return {
        "circuit": circuit,
        "stim_circuit": stim_circuit,
        "circuit_info": circuit_info,
        "qiskit_circuit": qiskit_circuit,
        "transpiled_circuit": transpiled_circuit,
        "dynamical_decoupling": dd_info,
        "stim_to_dense": stim_to_dense,
        "meas_order": meas_order,
        "mapping_info": mapping_info,
        "omit_initial_resets": omit_initial_resets,
        "omit_repeated_resets": omit_repeated_resets,
    }


def _raw_tuple_from_counts(
    backend: dict[str, Any],
    item: dict[str, Any],
    counts: dict[str, int],
    job: Any,
    batch_index: int,
    batch_size: int,
) -> tuple:
    from qec_pipeline.measurements import counts_to_measurement_array, virtualize_omitted_repeated_resets

    stim_circuit = item["stim_circuit"]
    circuit_info = item["circuit_info"]
    physical_measurements = counts_to_measurement_array(
        counts,
        num_measurements=stim_circuit.num_measurements,
        total_shots=int(backend["shots"]),
    )
    measurements = physical_measurements
    if item["omit_repeated_resets"]:
        measurements = virtualize_omitted_repeated_resets(
            physical_measurements,
            item["meas_order"],
        )

    raw_info = {
        "backend": backend["name"],
        "quantum_computer": backend.get("options", {}).get("quantum_computer", "emerald"),
        "shots": int(backend["shots"]),
        "job_id": job.job_id(),
        "batch_index": batch_index,
        "batch_size": batch_size,
        "qiskit_depth": item["qiskit_circuit"].depth(),
        "transpiled_depth": item["transpiled_circuit"].depth(),
        "qiskit_ops": dict(item["qiskit_circuit"].count_ops()),
        "transpiled_ops": dict(item["transpiled_circuit"].count_ops()),
        "dynamical_decoupling": item.get("dynamical_decoupling"),
        "omit_initial_resets": item["omit_initial_resets"],
        "omit_repeated_resets": item["omit_repeated_resets"],
        "measurement_record": (
            "virtual_reset_from_no_reset_hardware"
            if item["omit_repeated_resets"]
            else "physical_qiskit_clbit_order"
        ),
        "physical_measurement_one_rate": (
            physical_measurements.mean(axis=0).tolist()
            if item["omit_repeated_resets"]
            else None
        ),
        "stim_to_dense": item["stim_to_dense"],
        "meas_order": item["meas_order"],
        "mapping": item["mapping_info"],
        "noise_model": circuit_info.get("noise_model"),
        "implemented_noise_model": circuit_info.get("implemented_noise_model"),
        "calibration_noise": circuit_info.get("calibration_noise"),
        "basis": circuit_info["basis"],
        "qiskit_circuit_text": str(item["qiskit_circuit"]),
        "transpiled_circuit_text": str(item["transpiled_circuit"]),
    }

    return measurements, counts, raw_info


def _provider_args(options: dict[str, Any]) -> dict[str, Any]:
    provider_args = {
        "quantum_computer": options.get(
            "quantum_computer",
            os.environ.get("IQM_QUANTUM_COMPUTER", "emerald"),
        )
    }
    if "token" in options:
        provider_args["token"] = options["token"]
    return provider_args


def _optional_transpile_kwargs(options: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "seed_transpiler",
        "layout_method",
        "routing_method",
        "translation_method",
        "scheduling_method",
        "approximation_degree",
    ]
    return {
        key: options[key]
        for key in keys
        if key in options
    }


def _maybe_apply_dynamical_decoupling(
    circuit: Any,
    backend: Any,
    options: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    if not bool(options.get("dynamical_decoupling", False)):
        return circuit, {"enabled": False}

    try:
        from qiskit.circuit.library import XGate
        from qiskit.transpiler import PassManager
        from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling

        durations = backend.target.durations()
        sequence_name = str(options.get("dd_sequence", "xx")).lower()
        if sequence_name == "x_x":
            sequence_name = "xx"
        if sequence_name != "xx":
            raise ValueError(f"unsupported dd_sequence={sequence_name!r}; supported: xx")

        pass_manager = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDynamicalDecoupling(durations, [XGate(), XGate()]),
            ]
        )
        return pass_manager.run(circuit), {
            "enabled": True,
            "applied": True,
            "sequence": sequence_name,
        }
    except Exception as exc:
        return circuit, {
            "enabled": True,
            "applied": False,
            "error": str(exc),
        }
