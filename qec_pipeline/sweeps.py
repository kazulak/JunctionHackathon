from __future__ import annotations

import copy
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from qec_pipeline.pipeline import run_pipeline


def round_values(start: int, stop: int, points: int) -> list[int]:
    """Return inclusive integer round values from start to stop."""
    if start <= 0 or stop <= 0:
        raise ValueError("round values must be positive")
    if points <= 0:
        raise ValueError("points must be positive")
    if points == 1:
        return [start]

    step = (stop - start) / (points - 1)
    values = [int(round(start + index * step)) for index in range(points)]
    unique_values = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)

    if len(unique_values) != len(values):
        raise ValueError(
            "round range produced duplicate integer values; use fewer points or a wider range"
        )
    return unique_values


def run_rounds_sweep(
    base_config: dict[str, Any],
    rounds: list[int],
    output_root: Path | None = None,
) -> Path:
    """Run one pipeline job per round value and write CSV/JSON/plot summary."""
    base_name = base_config["experiment"]["name"]
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    root = output_root or Path(base_config["artifacts"].get("root", "results"))
    sweep_dir = root / f"{base_name}_rounds_sweep" / timestamp
    runs_root = sweep_dir / "runs"
    sweep_dir.mkdir(parents=True, exist_ok=False)

    rows = []
    for rounds_value in rounds:
        config = copy.deepcopy(base_config)
        config["code"]["rounds"] = int(rounds_value)
        config["experiment"]["name"] = f"{base_name}_rounds_{rounds_value}"
        config["artifacts"]["root"] = str(runs_root)

        run_dir, basis_results, notes = run_pipeline(config)
        for basis, _circuit, _raw, _syndromes, _decoded, metrics in basis_results:
            rows.append(
                {
                    "rounds": int(rounds_value),
                    "basis": basis,
                    "ler": float(metrics["ler"]),
                    "uncertainty": float(metrics["uncertainty"]),
                    "logical_failures": int(metrics["logical_failures"]),
                    "shots": int(metrics["shots"]),
                    "run_dir": str(run_dir),
                    "notes": "; ".join(notes),
                }
            )

    _write_sweep_outputs(sweep_dir, base_config, rounds, rows)
    return sweep_dir


def _write_sweep_outputs(
    sweep_dir: Path,
    base_config: dict[str, Any],
    rounds: list[int],
    rows: list[dict[str, Any]],
) -> None:
    csv_path = sweep_dir / "sweep_results.csv"
    fieldnames = [
        "rounds",
        "basis",
        "ler",
        "uncertainty",
        "logical_failures",
        "shots",
        "run_dir",
        "notes",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path = sweep_dir / "sweep_results.json"
    json_path.write_text(
        json.dumps(
            {
                "base_experiment": base_config["experiment"]["name"],
                "rounds": rounds,
                "rows": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    plot_path = sweep_dir / "ler_vs_rounds.png"
    plot_ler_vs_rounds(rows, plot_path)

    summary_lines = [
        f"# Rounds Sweep: {base_config['experiment']['name']}",
        "",
        f"- Rounds: {rounds}",
        f"- Results CSV: `{csv_path.name}`",
        f"- Results JSON: `{json_path.name}`",
        f"- Plot: `{plot_path.name}`",
        "",
        "## Results",
        "",
        "| Rounds | Basis | LER | Uncertainty | Failures | Shots |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row['rounds']} | {row['basis']} | {row['ler']} | "
            f"{row['uncertainty']} | {row['logical_failures']} | {row['shots']} |"
        )
    (sweep_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def plot_ler_vs_rounds(rows: list[dict[str, Any]], output_path: Path) -> None:
    """Plot LER against rounds, one line per basis."""
    if not rows:
        raise ValueError("cannot plot an empty sweep")

    bases = sorted({row["basis"] for row in rows})
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for basis in bases:
        basis_rows = sorted(
            [row for row in rows if row["basis"] == basis],
            key=lambda row: row["rounds"],
        )
        xs = [row["rounds"] for row in basis_rows]
        ys = [row["ler"] for row in basis_rows]
        yerr = [row["uncertainty"] for row in basis_rows]
        ax.errorbar(xs, ys, yerr=yerr, marker="o", capsize=4, label=basis)

    # ax.axhline(0.5, color="0.4", linestyle="--", linewidth=1, label="0.5 saturation")
    ax.set_xlabel("Rounds")
    ax.set_ylabel("Logical error rate")
    ax.set_title("LER vs rounds")
    ax.set_ylim(bottom=0.0, top=1.0)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
