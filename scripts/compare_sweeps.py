"""Compare several rounds sweeps: per-round fits, tables, and plots.

python scripts/compare_sweeps.py hardware=results/<sweep>/<ts> model=results/<sweep>/<ts> --output <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.analysis.metrics import fit_per_round_error, is_postselected, per_round_ler
from qec_pipeline.analysis.plots import plot_vs_rounds
from qec_pipeline.analysis.tables import fmt, read_sweep_csv, wilson_text, write_csv
from qec_pipeline.artifacts import utc_timestamp

SERIES = ("label", "basis")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("series", nargs="+", help="label=SWEEP_DIR_OR_CSV, e.g. baseline=results/run/sweep_results.csv")
    parser.add_argument("--output", type=Path, default=None, help="Defaults to results/comparisons/<timestamp>.")
    args = parser.parse_args()

    rows = []
    for item in args.series:
        label, path = _parse_series_arg(item)
        rows.extend(_read_rows(label, path))

    output_dir = args.output or Path("results") / "comparisons" / utc_timestamp()
    output_dir.mkdir(parents=True, exist_ok=False)

    fit_rows = _fit_all(rows)
    write_csv(output_dir / "comparison_results.csv", rows)
    write_csv(output_dir / "per_round_fit.csv", fit_rows)
    (output_dir / "comparison_results.json").write_text(
        json.dumps({"rows": rows, "fits": fit_rows}, indent=2) + "\n", encoding="utf-8"
    )

    common = {"series": SERIES, "figsize": (8, 4.8)}
    plot_vs_rounds(
        rows,
        output_dir / "ler_comparison.png",
        "ler",
        "Logical error rate",
        "LER vs rounds",
        yerr_key="uncertainty",
        y_max=0.55,
        chance_line=True,
        **common,
    )
    plot_vs_rounds(
        rows,
        output_dir / "per_round_ler_comparison.png",
        "logical_error_per_round",
        "Logical error per round",
        "Per-round logical error vs rounds",
        yerr_key="logical_error_per_round_uncertainty",
        y_max=None,
        **common,
    )
    plot_vs_rounds(
        rows,
        output_dir / "detector_rate_comparison.png",
        "mean_detector_firing_rate",
        "Mean detector firing rate",
        "Detector rate vs rounds",
        y_max=0.55,
        **common,
    )

    _write_summary(output_dir, rows, fit_rows)
    print(f"Comparison artifacts: {output_dir}")
    print(f"LER plot: {output_dir / 'ler_comparison.png'}")
    print(f"Fit CSV: {output_dir / 'per_round_fit.csv'}")
    return 0


def _parse_series_arg(item: str) -> tuple[str, Path]:
    if "=" not in item:
        raise SystemExit(f"Expected label=path, got: {item}")
    label, raw_path = item.split("=", 1)
    if not label:
        raise SystemExit(f"Missing label in: {item}")
    path = Path(raw_path)
    if path.is_dir():
        path = path / "sweep_results.csv"
    if not path.exists():
        raise SystemExit(f"Missing sweep CSV: {path}")
    return label, path


def _read_rows(label: str, path: Path) -> list[dict[str, Any]]:
    """Sweep rows with a per-round LER (recomputed for old CSVs; blank for postselected rows)."""
    rows = []
    for row in read_sweep_csv(path):
        postselected = is_postselected(row)
        per_round, per_round_sigma = (
            (None, None) if postselected else per_round_ler(row["ler"], row["uncertainty"], row["rounds"])
        )

        rows.append(
            {
                "label": label,
                "basis": row["basis"],
                "rounds": row["rounds"],
                "ler": row["ler"],
                "uncertainty": row["uncertainty"],
                "logical_error_per_round": None
                if postselected
                else _value_or(row, "logical_error_per_round", per_round),
                "logical_error_per_round_uncertainty": (
                    None if postselected else _value_or(row, "logical_error_per_round_uncertainty", per_round_sigma)
                ),
                "mean_detector_firing_rate": row.get("mean_detector_firing_rate"),
                "max_detector_firing_rate": row.get("max_detector_firing_rate"),
                "mean_syndrome_weight": row.get("mean_syndrome_weight"),
                "original_shots": _value_or(row, "original_shots", row["shots"]),
                "kept_shots": _value_or(row, "kept_shots", row["shots"]),
                "postselection_fraction": _value_or(row, "postselection_fraction", 1.0),
                "logical_failures": row["logical_failures"],
                "shots": row["shots"],
                "source_csv": str(path),
            }
        )
    return rows


def _value_or(row: dict[str, Any], key: str, fallback: Any) -> Any:
    return fallback if row.get(key) is None else row[key]


def _fit_all(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fit_rows = []
    for label, basis in sorted({(row["label"], row["basis"]) for row in rows}):
        series = sorted((r for r in rows if r["label"] == label and r["basis"] == basis), key=lambda r: r["rounds"])
        fit = fit_per_round_error(series)
        excluded = fit.pop("excluded_points")
        fit_rows.append({"label": label, "basis": basis, **fit, "excluded_points": len(excluded)})
    return fit_rows


def _write_summary(output_dir: Path, rows: list[dict[str, Any]], fit_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Sweep Comparison",
        "",
        "## Per-Round Fits",
        "",
        "Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2. "
        "Postselected series are excluded (their kept fraction changes with r).",
        "",
        "| Label | Basis | Fit points | Error per round | 1-sigma | Amplitude A | Excluded points |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in fit_rows:
        lines.append(
            f"| {row['label']} | {row['basis']} | {row['fit_points']} | "
            f"{fmt(row['fitted_logical_error_per_round'], 6)} | "
            f"{fmt(row['fitted_logical_error_per_round_uncertainty'], 6)} | "
            f"{fmt(row['fit_amplitude'], 6)} | {row['excluded_points']} |"
        )
    lines += [
        "",
        "## Sweep Rows",
        "",
        "| Label | Basis | Rounds | LER | 68% Wilson interval | Per-round LER | Mean detector rate "
        "| Kept fraction | Failures | Shots |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(rows, key=lambda item: (item["label"], item["basis"], item["rounds"])):
        lines.append(
            f"| {row['label']} | {row['basis']} | {row['rounds']} | {fmt(row['ler'], 6)} | "
            f"{wilson_text(row['logical_failures'], row['shots'])} | {fmt(row['logical_error_per_round'], 6)} | "
            f"{fmt(row.get('mean_detector_firing_rate'), 6)} | {fmt(row.get('postselection_fraction'), 6)} | "
            f"{row['logical_failures']} | {row['shots']} |"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
