"""Reading and writing result tables (sweep CSVs, Markdown cells), shared by the pipeline and scripts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from qec_pipeline.analysis.metrics import wilson_interval

SWEEP_COLUMNS = [
    "rounds",
    "basis",
    "ler",
    "uncertainty",
    "ler_ci_low",
    "ler_ci_high",
    "logical_error_per_round",
    "logical_error_per_round_uncertainty",
    "logical_failures",
    "shots",
    "mean_detector_firing_rate",
    "max_detector_firing_rate",
    "mean_syndrome_weight",
    "original_shots",
    "kept_shots",
    "postselection_fraction",
    "selection_is_in_sample",
    "run_dir",
    "notes",
]
_INT_COLUMNS = {"rounds", "logical_failures", "shots", "original_shots", "kept_shots"}
_FLOAT_COLUMNS = {
    "ler",
    "uncertainty",
    "ler_ci_low",
    "ler_ci_high",
    "logical_error_per_round",
    "logical_error_per_round_uncertainty",
    "mean_detector_firing_rate",
    "max_detector_firing_rate",
    "mean_syndrome_weight",
    "postselection_fraction",
}


def read_sweep_csv(path: Path) -> list[dict[str, Any]]:
    """Rows of a `sweep_results.csv` with numbers parsed; empty cells become None."""
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = dict(raw)
            for key, value in raw.items():
                if value in {None, ""}:
                    row[key] = None
                elif key in _INT_COLUMNS:
                    row[key] = int(float(value))
                elif key in _FLOAT_COLUMNS:
                    row[key] = float(value)
            rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    """Write dict rows; list and dict cells are stored as JSON."""
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def fmt(value: Any, digits: int = 4) -> str:
    """Number for a Markdown cell, blank for missing values."""
    if value in {None, ""}:
        return ""
    return f"{float(value):.{digits}g}"


def wilson_text(failures: int, shots: int) -> str:
    """The ~68% Wilson interval as 'low–high', blank without shots."""
    if not shots:
        return ""
    low, high = wilson_interval(int(failures), int(shots))
    return f"{low:.4g}–{high:.4g}"
