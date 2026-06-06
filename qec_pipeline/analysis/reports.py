from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qec_pipeline.types import BasisRunResult, CircuitResult, RawResult, SyndromeResult


def write_run_summary(
    run_dir: Path,
    config: dict[str, Any],
    basis_results: list[BasisRunResult],
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
                f"- Artifacts: `{basis}/`",
                "",
            ]
        )

    if notes:
        lines.extend(["## Notes", ""])
        lines.extend(f"- {note}" for note in notes)

    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_artifacts(
    run_dir: Path,
    circuit: CircuitResult,
    raw: RawResult,
    syndromes: SyndromeResult,
    metrics: dict[str, Any],
) -> None:
    """Write inspectable files for one basis run."""
    stim_circuit, _detector_model, _measurement_order, circuit_info = circuit
    measurements, _counts, raw_info = raw
    detection_events, observable_flips, syndrome_info = syndromes

    (run_dir / "circuit.stim").write_text(str(stim_circuit), encoding="utf-8")
    _write_json(run_dir / "circuit_metadata.json", circuit_info)
    _write_json(run_dir / "raw_metadata.json", raw_info)
    _write_json(run_dir / "syndrome_metadata.json", syndrome_info)
    _write_json(run_dir / "metrics.json", metrics)

    _write_table_head(run_dir / "raw_measurements_head.csv", measurements, max_rows=10)
    _write_table_head(run_dir / "detection_events_head.csv", detection_events, max_rows=10)
    _write_table_head(run_dir / "observable_flips_head.csv", observable_flips, max_rows=10)


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
