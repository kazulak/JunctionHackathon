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
    iqm_backend, prepared, compile_options = prepare_iqm_batch(backend, requests)
    transpiled_circuits = [item["transpiled_circuit"] for item in prepared]
    job = iqm_backend.run(
        transpiled_circuits,
        shots=int(backend["shots"]),
        circuit_compilation_options=compile_options,
    )
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


def prepare_iqm_batch(
    backend: dict[str, Any],
    requests: list[dict[str, Any]],
) -> tuple[Any, list[dict[str, Any]], Any]:
    """Connect, convert, transpile, and validate a batch WITHOUT submitting it.

    Also builds the IQM run request, so anything the server-side client would reject
    fails here. Used both by the real submission and by preflight checks.
    """
    options = backend.get("options", {}) or {}
    _validate_backend_options(options)
    _load_dotenv()

    from iqm.qiskit_iqm import IQMProvider

    provider = IQMProvider(
        options.get("server_url", os.environ.get("IQM_SERVER_URL", "https://resonance.meetiqm.com")),
        **_provider_args(options),
    )
    iqm_backend = provider.get_backend()
    prepared = [
        _prepare_iqm_request(backend, request["circuit"], request.get("mapping"), iqm_backend)
        for request in requests
    ]
    compile_options = circuit_compilation_options(options)
    run_request = iqm_backend.create_run_request(
        [item["transpiled_circuit"] for item in prepared],
        shots=int(backend["shots"]),
        circuit_compilation_options=compile_options,
    )
    _check_calibration_is_current(run_request.calibration_set_id, requests, options)
    return iqm_backend, prepared, compile_options


def _check_calibration_is_current(
    live_calibration_set_id: Any,
    requests: list[dict[str, Any]],
    options: dict[str, Any],
) -> None:
    """Refuse to submit when patch selection / noise used a different calibration than the QPU has now.

    IQM recalibrates regularly; a stale file means the chosen qubits and the decoder's
    priors describe a device state that no longer exists. Refresh with
    `scripts/fetch_calibration.py`, or set `backend.options.allow_stale_calibration: true`.
    """
    if live_calibration_set_id is None or bool(options.get("allow_stale_calibration", False)):
        return
    used = set()
    for request in requests:
        info = request["circuit"][3]
        for path in {info.get("noise_calibration_file"), (request.get("mapping") or {}).get("calibration_file")}:
            if not path or not Path(path).exists():
                continue
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
            except ValueError:
                continue  # not a JSON observation set (e.g. a hand-written YAML grid)
            set_id = data.get("calibration_set_id") or data.get("describes_id")
            if set_id:
                used.add((str(set_id), str(path)))
    stale = sorted(path for set_id, path in used if set_id != str(live_calibration_set_id))
    if stale:
        raise RuntimeError(
            f"QPU is on calibration set {live_calibration_set_id}, but these files describe another set: {stale}. "
            "Run scripts/fetch_calibration.py and update the config (or allow_stale_calibration: true)."
        )


def circuit_compilation_options(options: dict[str, Any]) -> Any:
    """IQM server-side compilation options from `backend.options`.

    - `active_reset_cycles`: actively reset qubits between shots instead of waiting
      ~400 us for relaxation; reduces QPU time (and credits) per shot by >20x.
    - `dynamical_decoupling`: IQM's native DD on idling qubits (e.g. data qubits
      during ancilla readout), as recommended by Google's surface-code experiments.
    - `max_circuit_duration_over_t2`: server-side circuit-duration guard.
    """
    from iqm.iqm_client import CircuitCompilationOptions, DDMode

    kwargs: dict[str, Any] = {}
    if options.get("active_reset_cycles") is not None:
        kwargs["active_reset_cycles"] = int(options["active_reset_cycles"])
    if bool(options.get("dynamical_decoupling", False)):
        kwargs["dd_mode"] = DDMode.ENABLED
    if options.get("max_circuit_duration_over_t2") is not None:
        kwargs["max_circuit_duration_over_t2"] = float(options["max_circuit_duration_over_t2"])
    return CircuitCompilationOptions(**kwargs)


def _validate_backend_options(options: dict[str, Any]) -> None:
    """Reject options that would be silently ignored or that moved, before any IQM connection."""
    for moved in ("omit_repeated_resets", "mid_circuit_reset"):
        if moved in options:
            raise ValueError(
                f"backend.options.{moved} is no longer supported: the reset strategy changes the "
                "circuit and its detector error model, so set `code.mid_circuit_reset` "
                "(reset | feedforward | none) instead."
            )
    if "dd_sequence" in options:
        raise ValueError("backend.options.dd_sequence is not supported; IQM's standard DD strategy is used.")


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
    from qiskit import transpile

    from qec_pipeline.conversion import stim_to_qiskit_minimal
    from qec_pipeline.mapping import select_mapping_from_config

    stim_circuit, _detector_model, _measurement_order, circuit_info = circuit
    options = backend.get("options", {})
    omit_initial_resets = bool(options.get("omit_initial_resets", False))
    qiskit_circuit, stim_to_dense, meas_order = stim_to_qiskit_minimal(
        stim_circuit,
        omit_initial_resets=omit_initial_resets,
        group_measurements=bool(options.get("group_measurements", True)),
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
        "mid_circuit_reset": circuit_info.get("mid_circuit_reset", "reset"),
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
    from qec_pipeline.measurements import counts_to_measurement_array, memory_to_measurement_array

    stim_circuit = item["stim_circuit"]
    circuit_info = item["circuit_info"]
    # Records are decoded against the same Stim circuit that encodes the reset
    # strategy, so raw records are used directly (no software virtualization).
    if memory is not None:
        measurements = memory_to_measurement_array(memory, stim_circuit.num_measurements)
    else:
        measurements = counts_to_measurement_array(
            counts,
            num_measurements=stim_circuit.num_measurements,
            total_shots=int(backend["shots"]),
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
        "mid_circuit_reset": item["mid_circuit_reset"],
        "compilation_options": _compilation_options_record(backend.get("options", {}) or {}),
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


def _compilation_options_record(options: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_reset_cycles": options.get("active_reset_cycles"),
        "dynamical_decoupling": bool(options.get("dynamical_decoupling", False)),
        "max_circuit_duration_over_t2": options.get("max_circuit_duration_over_t2"),
    }


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
