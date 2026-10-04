from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
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
    _validate_backend_options(backend.get("options", {}) or {})
    _load_dotenv()

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
        counts = result.get_counts(index)
        memory = _memory_or_none(result, index)
        calibration_set_id = getattr(result.results[index], "calibration_set_id", None)
        raws.append(
            _raw_tuple_from_counts(
                backend,
                item,
                counts,
                job,
                index,
                batch_size,
                memory=memory,
                calibration_set_id=calibration_set_id,
            )
        )
    return raws


def _validate_backend_options(options: dict[str, Any]) -> None:
    """Reject options that would be silently ignored, before any IQM connection."""
    if bool(options.get("dynamical_decoupling", False)):
        raise ValueError(
            "backend.options.dynamical_decoupling is not implemented for IQM backends. "
            "The previous implementation failed silently (ERRATA E6); remove the option."
        )


def _memory_or_none(result: Any, index: int) -> list[str] | None:
    """Per-shot bitstrings in shot order, or None if the backend did not return them."""
    try:
        return list(result.get_memory(index))
    except Exception:  # noqa: BLE001 - Qiskit raises QiskitError subclasses without memory
        return None


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
    loci = physical_loci(transpiled_circuit, iqm_backend)
    _check_layout_matches_mapping(loci, mapping_info)

    return {
        "circuit": circuit,
        "stim_circuit": stim_circuit,
        "circuit_info": circuit_info,
        "qiskit_circuit": qiskit_circuit,
        "transpiled_circuit": transpiled_circuit,
        "physical_loci": loci,
        "calibration_file_age": _calibration_file_age(mapping or {}, circuit_info),
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
    memory: list[str] | None = None,
    calibration_set_id: Any = None,
) -> tuple:
    from qec_pipeline.measurements import (
        counts_to_measurement_array,
        memory_to_measurement_array,
        virtualize_omitted_repeated_resets,
    )

    stim_circuit = item["stim_circuit"]
    circuit_info = item["circuit_info"]
    if memory is not None:
        physical_measurements = memory_to_measurement_array(memory, stim_circuit.num_measurements)
    else:
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
        "transpilation_metrics": _transpilation_metrics(
            dict(item["qiskit_circuit"].count_ops()),
            dict(item["transpiled_circuit"].count_ops()),
            item["qiskit_circuit"].depth(),
            item["transpiled_circuit"].depth(),
            item["mapping_info"],
        ),
        "shot_order_preserved": memory is not None,
        "calibration_set_id": str(calibration_set_id) if calibration_set_id else None,
        "calibration_file_age": item.get("calibration_file_age"),
        "physical_loci": item.get("physical_loci"),
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
        "transpiled_circuit_text": TRANSPILED_DRAWING_HEADER + str(item["transpiled_circuit"]),
    }

    return measurements, counts, raw_info


def _transpilation_metrics(
    qiskit_ops: dict[str, int],
    transpiled_ops: dict[str, int],
    qiskit_depth: int,
    transpiled_depth: int,
    mapping_info: dict[str, Any] | None,
) -> dict[str, Any]:
    qiskit_two_qubit = _two_qubit_gate_count(qiskit_ops)
    transpiled_two_qubit = _two_qubit_gate_count(transpiled_ops)
    return {
        "qiskit_depth": int(qiskit_depth),
        "transpiled_depth": int(transpiled_depth),
        "depth_ratio": float(transpiled_depth / qiskit_depth) if qiskit_depth else 0.0,
        "qiskit_two_qubit_gate_count": qiskit_two_qubit,
        "transpiled_two_qubit_gate_count": transpiled_two_qubit,
        "added_two_qubit_gate_count": transpiled_two_qubit - qiskit_two_qubit,
        "swap_count": int(transpiled_ops.get("swap", 0)),
        "qiskit_swap_count": int(qiskit_ops.get("swap", 0)),
        "transpiled_swap_count": int(transpiled_ops.get("swap", 0)),
        "expected_swap_count_from_mapping": (
            mapping_info.get("expected_swap_count") if mapping_info else None
        ),
        "native_code_edges": mapping_info.get("native_code_edges") if mapping_info else None,
        "routed_code_edges": mapping_info.get("routed_code_edges") if mapping_info else None,
        "unique_code_edges": mapping_info.get("unique_code_edges") if mapping_info else None,
    }


def _two_qubit_gate_count(ops: dict[str, int]) -> int:
    two_qubit_names = {
        "cx",
        "cz",
        "swap",
        "ecr",
        "iswap",
        "rxx",
        "ryy",
        "rzz",
        "move",
    }
    return int(sum(count for name, count in ops.items() if name.lower() in two_qubit_names))


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


def _load_dotenv() -> None:
    repo_env = Path(__file__).resolve().parents[2] / ".env"
    if not repo_env.exists():
        return

    for line in repo_env.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        if text.startswith("export "):
            text = text[len("export ") :].strip()
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


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


TRANSPILED_DRAWING_HEADER = (
    "# IQM's transpiler keeps qubits in virtual order, so the wire labels below are NOT\n"
    "# the physical qubits. The physical loci sent to the QPU are in raw_metadata.json\n"
    "# under physical_loci.\n\n"
)


def physical_loci(transpiled_circuit: Any, iqm_backend: Any) -> dict[str, Any]:
    """Serialize the circuit the way IQM does and return the physical qubits it acts on."""
    from iqm.qiskit_iqm.qiskit_to_iqm import serialize_instructions

    index_to_name = {
        index: iqm_backend.index_to_qubit_name(index) for index in range(transpiled_circuit.num_qubits)
    }
    instructions = serialize_instructions(transpiled_circuit, index_to_name)
    qubits = sorted({name for op in instructions for name in op.locus}, key=_qubit_sort_key)
    two_qubit = sorted({tuple(op.locus) for op in instructions if len(op.locus) == 2})
    measured = sorted(
        {name for op in instructions if op.name == "measure" for name in op.locus},
        key=_qubit_sort_key,
    )
    return {
        "physical_qubits": qubits,
        "measured_qubits": measured,
        "two_qubit_loci": [list(pair) for pair in two_qubit],
    }


def _check_layout_matches_mapping(loci: dict[str, Any], mapping_info: dict[str, Any] | None) -> None:
    """Fail before submission if a native patch would run on different qubits."""
    if not mapping_info or not mapping_info.get("dense_to_hardware"):
        return
    intended = set(mapping_info["dense_to_hardware"].values())
    actual = set(loci["physical_qubits"])
    routed = bool(mapping_info.get("routed_code_edges")) or mapping_info.get("strategy") == "calibration_routed_layout"
    if actual != intended and not routed:
        raise RuntimeError(
            "Transpiled circuit does not act on the selected patch: "
            f"unexpected={sorted(actual - intended)}, unused={sorted(intended - actual)}"
        )


def _calibration_file_age(mapping: dict[str, Any], circuit_info: dict[str, Any]) -> dict[str, Any] | None:
    """How old the calibration snapshot used for mapping/noise was at submission time."""
    calibration_file = circuit_info.get("noise_calibration_file") or mapping.get("calibration_file")
    if not calibration_file or not Path(calibration_file).exists():
        return None
    try:
        created = json.loads(Path(calibration_file).read_text(encoding="utf-8")).get("created_timestamp")
    except (OSError, ValueError):
        return None
    if not created:
        return None
    created_at = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    age_hours = (datetime.now(UTC) - created_at).total_seconds() / 3600.0
    return {"file": str(calibration_file), "created_utc": str(created), "age_hours_at_submission": age_hours}


def _qubit_sort_key(label: str) -> tuple[int, int | str]:
    text = str(label)
    if text.upper().startswith("QB") and text[2:].isdigit():
        return (0, int(text[2:]))
    return (1, text)
