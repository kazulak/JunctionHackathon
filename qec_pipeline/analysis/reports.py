from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from qec_pipeline.analysis.diagnostics import build_run_diagnostics
from qec_pipeline.analysis.measurement_diagnostics import build_measurement_diagnostics


def write_run_summary(
    run_dir: Path,
    config: dict[str, Any],
    basis_results: list[tuple],
    notes: list[str],
) -> None:
    """Write `summary.md` for the whole experiment."""
    lines = [
        f"# Run Summary: {config['experiment']['name']}",
        "",
        "## Config",
        "",
        f"- Code: {config['code']['family']}, d={config['code']['distance']}, "
        f"rounds={config['code']['rounds']}",
        f"- Basis: {config['code']['basis']}",
        f"- Reset: {config['code']['reset_mode']}",
        f"- Backend: {config['backend']['name']}, shots={config['backend']['shots']}",
        f"- Noise: {config['noise']['model']}",
        f"- Decoder: {config['decoder']['name']}",
        "",
        "## Results",
        "",
    ]

    for basis, _circuit, _raw, _syndromes, decoded, _metrics in basis_results:
        _predicted, _failures, ler, uncertainty, decoder_info = decoded
        lines.extend(
            [
                f"### {basis}",
                "",
                f"- LER: {ler}",
                f"- Uncertainty: {uncertainty}",
                f"- Logical failures: {decoder_info['logical_failures']}",
            ]
        )
        if "logical_error_per_round" in _metrics:
            lines.extend(
                [
                    f"- Logical error per round: {_metrics['logical_error_per_round']}",
                    "- Logical error per round uncertainty: "
                    f"{_metrics['logical_error_per_round_uncertainty']}",
                ]
            )
        lines.extend([f"- Artifacts: `{basis}/`", ""])

    if notes:
        lines.extend(["## Notes", ""])
        lines.extend(f"- {note}" for note in notes)

    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_artifacts(
    run_dir: Path,
    circuit: tuple,
    raw: tuple,
    syndromes: tuple,
    metrics: dict[str, Any],
    artifacts: dict[str, Any] | None = None,
) -> None:
    """Write inspectable files for one basis run."""
    artifacts = artifacts or {}
    stim_circuit, _detector_model, _measurement_order, circuit_info = circuit
    measurements, counts, raw_info = raw
    detection_events, observable_flips, syndrome_info = syndromes

    (run_dir / "circuit.stim").write_text(str(stim_circuit), encoding="utf-8")
    _write_json(run_dir / "circuit_metadata.json", circuit_info)
    raw_info_for_json = dict(raw_info)
    qiskit_circuit_text = raw_info_for_json.pop("qiskit_circuit_text", None)
    transpiled_circuit_text = raw_info_for_json.pop("transpiled_circuit_text", None)
    if hasattr(measurements, "mean") and getattr(measurements, "size", 0):
        raw_info_for_json["measurement_one_rate"] = measurements.mean(axis=0)
        raw_info_for_json["mean_measurement_one_rate"] = float(measurements.mean())

    _write_json(run_dir / "raw_metadata.json", raw_info_for_json)
    _write_json(run_dir / "syndrome_metadata.json", syndrome_info)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(
        run_dir / "diagnostics.json",
        build_run_diagnostics(circuit_info, raw_info_for_json, syndrome_info, metrics),
    )
    _write_json(
        run_dir / "measurement_diagnostics.json",
        build_measurement_diagnostics(stim_circuit, measurements, raw_info_for_json),
    )
    if counts is not None:
        _write_json(run_dir / "counts.json", counts)
    if qiskit_circuit_text is not None:
        (run_dir / "qiskit_circuit.txt").write_text(qiskit_circuit_text, encoding="utf-8")
    if transpiled_circuit_text is not None:
        (run_dir / "transpiled_circuit.txt").write_text(
            transpiled_circuit_text,
            encoding="utf-8",
        )

    _write_table_head(run_dir / "raw_measurements_head.csv", measurements, max_rows=10)
    _write_table_head(run_dir / "detection_events_head.csv", detection_events, max_rows=10)
    _write_table_head(run_dir / "observable_flips_head.csv", observable_flips, max_rows=10)
    if bool(artifacts.get("save_raw_measurements", False)):
        np.savez_compressed(run_dir / "raw_measurements.npz", measurements=measurements)
    if bool(artifacts.get("save_syndromes", False)):
        np.savez_compressed(
            run_dir / "syndromes.npz",
            detection_events=detection_events,
            observable_flips=observable_flips,
        )


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(_jsonable(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_table_head(path: Path, table: object, max_rows: int) -> None:
    rows = _rows(table)[:max_rows]
    text = "\n".join(",".join("1" if bool(value) else "0" for value in row) for row in rows)
    path.write_text(text + "\n", encoding="utf-8")


def _rows(table: object) -> list[list[object]]:
    if hasattr(table, "tolist"):
        return table.tolist()
    return list(table)


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return value
