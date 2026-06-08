from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare multiple rounds sweeps and fit logical error per round."
    )
    parser.add_argument(
        "series",
        nargs="+",
        help="Series as label=SWEEP_DIR_OR_CSV, e.g. baseline=results/run/sweep_results.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory. Defaults to results/comparisons/<timestamp>.",
    )
    args = parser.parse_args()

    rows = []
    for item in args.series:
        label, path = _parse_series_arg(item)
        rows.extend(_read_rows(label, path))

    output_dir = args.output or Path("results") / "comparisons" / _timestamp()
    output_dir.mkdir(parents=True, exist_ok=False)

    fit_rows = _fit_all(rows)
    _write_csv(output_dir / "comparison_results.csv", rows)
    _write_csv(output_dir / "per_round_fit.csv", fit_rows)
    (output_dir / "comparison_results.json").write_text(
        json.dumps({"rows": rows, "fits": fit_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    _plot_metric(
        rows,
        output_dir / "ler_comparison.png",
        y_key="ler",
        yerr_key="uncertainty",
        ylabel="Logical error rate",
        title="LER vs rounds",
        y_max=0.55,
    )
    _plot_metric(
        rows,
        output_dir / "per_round_ler_comparison.png",
        y_key="logical_error_per_round",
        yerr_key="logical_error_per_round_uncertainty",
        ylabel="Logical error per round",
        title="Per-round logical error vs rounds",
        y_max=None,
    )
    if any(row.get("mean_detector_firing_rate") not in {None, ""} for row in rows):
        _plot_metric(
            rows,
            output_dir / "detector_rate_comparison.png",
            y_key="mean_detector_firing_rate",
            yerr_key=None,
            ylabel="Mean detector firing rate",
            title="Detector rate vs rounds",
            y_max=0.55,
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
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rounds = int(row["rounds"])
            ler = float(row["ler"])
            uncertainty = float(row["uncertainty"])
            per_round, per_round_uncertainty = _per_round_ler(
                ler,
                uncertainty,
                rounds,
            )
            rows.append(
                {
                    "label": label,
                    "basis": row["basis"],
                    "rounds": rounds,
                    "ler": ler,
                    "uncertainty": uncertainty,
                    "logical_error_per_round": _float_or(row, "logical_error_per_round", per_round),
                    "logical_error_per_round_uncertainty": _float_or(
                        row,
                        "logical_error_per_round_uncertainty",
                        per_round_uncertainty,
                    ),
                    "mean_detector_firing_rate": _float_or(row, "mean_detector_firing_rate", None),
                    "max_detector_firing_rate": _float_or(row, "max_detector_firing_rate", None),
                    "mean_syndrome_weight": _float_or(row, "mean_syndrome_weight", None),
                    "original_shots": _int_or(row, "original_shots", int(row["shots"])),
                    "kept_shots": _int_or(row, "kept_shots", int(row["shots"])),
                    "postselection_fraction": _float_or(row, "postselection_fraction", 1.0),
                    "logical_failures": int(row["logical_failures"]),
                    "shots": int(row["shots"]),
                    "source_csv": str(path),
                }
            )
    return rows


def _fit_all(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fit_rows = []
    keys = sorted({(row["label"], row["basis"]) for row in rows})
    for label, basis in keys:
        series = sorted(
            [row for row in rows if row["label"] == label and row["basis"] == basis],
            key=lambda row: row["rounds"],
        )
        fit = _fit_per_round_error(series)
        fit_rows.append({"label": label, "basis": basis, **fit})
    return fit_rows


def _fit_per_round_error(rows: list[dict[str, Any]]) -> dict[str, Any]:
    xs = []
    ys = []
    for row in rows:
        ler = float(row["ler"])
        if 0.0 <= ler < 0.5:
            survival = 1.0 - 2.0 * ler
            if survival > 0.0:
                xs.append(float(row["rounds"]))
                ys.append(math.log(survival))

    if len(xs) < 2:
        return {
            "fit_points": len(xs),
            "fitted_logical_error_per_round": None,
            "fit_slope": None,
            "fit_intercept": None,
        }

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0.0:
        slope = 0.0
    else:
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    intercept = mean_y - slope * mean_x
    per_round = (1.0 - math.exp(slope)) / 2.0
    return {
        "fit_points": len(xs),
        "fitted_logical_error_per_round": per_round,
        "fit_slope": slope,
        "fit_intercept": intercept,
    }


def _plot_metric(
    rows: list[dict[str, Any]],
    output_path: Path,
    y_key: str,
    yerr_key: str | None,
    ylabel: str,
    title: str,
    y_max: float | None,
) -> None:
    rows = [row for row in rows if row.get(y_key) not in {None, ""}]
    if not rows:
        return

    fig, ax = plt.subplots(figsize=(8, 4.8))
    keys = sorted({(row["label"], row["basis"]) for row in rows})
    for label, basis in keys:
        series = sorted(
            [row for row in rows if row["label"] == label and row["basis"] == basis],
            key=lambda row: row["rounds"],
        )
        xs = [row["rounds"] for row in series]
        ys = [float(row[y_key]) for row in series]
        yerr = None
        if yerr_key:
            yerr = [
                float(row[yerr_key])
                if row.get(yerr_key) not in {None, ""}
                else 0.0
                for row in series
            ]
        ax.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, label=f"{label} {basis}")

    if y_key == "ler":
        ax.axhline(0.5, color="0.4", linestyle="--", linewidth=1, label="random LER")
    ax.set_xlabel("Rounds")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(bottom=0.0, top=y_max)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize="small")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _write_summary(
    output_dir: Path,
    rows: list[dict[str, Any]],
    fit_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# Sweep Comparison",
        "",
        "## Per-Round Fits",
        "",
        "| Label | Basis | Fit points | Fitted logical error per round |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in fit_rows:
        value = row["fitted_logical_error_per_round"]
        value_text = "" if value is None else f"{value:.6g}"
        lines.append(f"| {row['label']} | {row['basis']} | {row['fit_points']} | {value_text} |")

    lines.extend(
        [
            "",
            "## Sweep Rows",
            "",
            "| Label | Basis | Rounds | LER | Uncertainty | Per-round LER | Mean detector rate | Kept fraction | Failures | Shots |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(rows, key=lambda item: (item["label"], item["basis"], item["rounds"])):
        lines.append(
            f"| {row['label']} | {row['basis']} | {row['rounds']} | "
            f"{row['ler']:.6g} | {row['uncertainty']:.3g} | "
            f"{row['logical_error_per_round']:.6g} | "
            f"{_format_optional(row.get('mean_detector_firing_rate'))} | "
            f"{_format_optional(row.get('postselection_fraction'))} | "
            f"{row['logical_failures']} | {row['shots']} |"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _per_round_ler(total_ler: float, total_uncertainty: float, rounds: int) -> tuple[float, float]:
    if rounds <= 1:
        return total_ler, total_uncertainty
    clamped = min(max(float(total_ler), 0.0), 0.499999999)
    survival = 1.0 - 2.0 * clamped
    per_round = (1.0 - survival ** (1.0 / rounds)) / 2.0
    derivative = (1.0 / rounds) * survival ** ((1.0 / rounds) - 1.0)
    return float(per_round), float(abs(derivative) * total_uncertainty)


def _float_or(row: dict[str, str], key: str, fallback: float | None) -> float | None:
    value = row.get(key)
    if value in {None, ""}:
        return fallback
    return float(value)


def _int_or(row: dict[str, str], key: str, fallback: int) -> int:
    value = row.get(key)
    if value in {None, ""}:
        return fallback
    return int(float(value))


def _format_optional(value: Any) -> str:
    if value in {None, ""}:
        return ""
    return f"{float(value):.6g}"


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
