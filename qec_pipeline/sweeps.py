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

from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends.iqm_hardware import run_iqm_hardware_batch_backend
from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.codes import get_code_builder
from qec_pipeline.decoders import get_decoder
from qec_pipeline.pipeline import run_pipeline
from qec_pipeline.syndromes import extract_detection_events


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
    if _use_iqm_batch_sweep(base_config):
        return _run_iqm_rounds_sweep_batch(base_config, rounds, output_root)

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
                    "logical_error_per_round": metrics.get("logical_error_per_round"),
                    "logical_error_per_round_uncertainty": metrics.get(
                        "logical_error_per_round_uncertainty"
                    ),
                    "logical_failures": int(metrics["logical_failures"]),
                    "shots": int(metrics["shots"]),
                    "run_dir": str(run_dir),
                    "notes": "; ".join(notes),
                }
            )

    _write_sweep_outputs(sweep_dir, base_config, rounds, rows)
    return sweep_dir


def _run_iqm_rounds_sweep_batch(
    base_config: dict[str, Any],
    rounds: list[int],
    output_root: Path | None = None,
) -> Path:
    """Submit all IQM sweep circuits in one batch before waiting for results."""
    base_name = base_config["experiment"]["name"]
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    root = output_root or Path(base_config["artifacts"].get("root", "results"))
    sweep_dir = root / f"{base_name}_rounds_sweep" / timestamp
    runs_root = sweep_dir / "runs"
    sweep_dir.mkdir(parents=True, exist_ok=False)

    jobs = []
    groups = []
    for rounds_value in rounds:
        config = copy.deepcopy(base_config)
        config["code"]["rounds"] = int(rounds_value)
        config["experiment"]["name"] = f"{base_name}_rounds_{rounds_value}"
        config["artifacts"]["root"] = str(runs_root)
        run_dir = prepare_run_directory(config)
        group = {
            "rounds": int(rounds_value),
            "config": config,
            "run_dir": run_dir,
            "basis_results": [],
            "notes": [],
        }
        groups.append(group)

        for basis in _basis_list(config["code"]["basis"]):
            circuit = get_code_builder(config["code"].get("family", "surface_code"))(
                config["code"],
                config["noise"],
                basis,
            )
            circuit = prepare_circuit_for_execution(config, circuit)
            jobs.append(
                {
                    "group": group,
                    "basis": basis,
                    "circuit": circuit,
                    "mapping": config["mapping"],
                    "decoder": config["decoder"],
                }
            )

    raws = run_iqm_hardware_batch_backend(
        base_config["backend"],
        [
            {"circuit": job["circuit"], "mapping": job["mapping"]}
            for job in jobs
        ],
    )

    rows = []
    for job, raw in zip(jobs, raws):
        group = job["group"]
        basis = job["basis"]
        circuit = job["circuit"]
        syndromes = extract_detection_events(circuit, raw)
        decoded = get_decoder(job["decoder"]["name"])(job["decoder"], circuit, syndromes)
        _predicted, _failures, ler, uncertainty, decoder_info = decoded
        metrics = {
            "basis": basis,
            "ler": ler,
            "uncertainty": uncertainty,
            "logical_failures": decoder_info["logical_failures"],
            "shots": decoder_info["shots"],
            "decoder_info": decoder_info,
        }
        if group["rounds"] > 1:
            per_round_ler, per_round_uncertainty = _per_round_ler(
                ler,
                uncertainty,
                group["rounds"],
            )
            metrics["rounds"] = group["rounds"]
            metrics["logical_error_per_round"] = per_round_ler
            metrics["logical_error_per_round_uncertainty"] = per_round_uncertainty
        if "noise_sweep" in decoder_info:
            metrics["decoder_noise_sweep"] = decoder_info["noise_sweep"]

        basis_run_dir = group["run_dir"] / basis
        basis_run_dir.mkdir(parents=True, exist_ok=False)
        write_run_artifacts(basis_run_dir, circuit, raw, syndromes, metrics)

        group["basis_results"].append((basis, circuit, raw, syndromes, decoded, metrics))
        note = f"{basis}: LER {ler} +/- {uncertainty}"
        group["notes"].append(note)
        rows.append(
            {
                "rounds": group["rounds"],
                "basis": basis,
                "ler": float(metrics["ler"]),
                "uncertainty": float(metrics["uncertainty"]),
                "logical_error_per_round": metrics.get("logical_error_per_round"),
                "logical_error_per_round_uncertainty": metrics.get(
                    "logical_error_per_round_uncertainty"
                ),
                "logical_failures": int(metrics["logical_failures"]),
                "shots": int(metrics["shots"]),
                "run_dir": str(group["run_dir"]),
                "notes": "; ".join(group["notes"]),
            }
        )

    for group in groups:
        write_run_summary(
            group["run_dir"],
            group["config"],
            group["basis_results"],
            group["notes"],
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
        "logical_error_per_round",
        "logical_error_per_round_uncertainty",
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
        "| Rounds | Basis | LER | Uncertainty | Per-round LER | Per-round uncertainty | Failures | Shots |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row['rounds']} | {row['basis']} | {row['ler']} | "
            f"{row['uncertainty']} | {row.get('logical_error_per_round', '')} | "
            f"{row.get('logical_error_per_round_uncertainty', '')} | "
            f"{row['logical_failures']} | {row['shots']} |"
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


def _use_iqm_batch_sweep(config: dict[str, Any]) -> bool:
    if config["backend"].get("name") != "iqm_hardware":
        return False
    return bool(config["backend"].get("options", {}).get("batch_submit", True))


def _basis_list(config_basis: str) -> list[str]:
    if config_basis == "both":
        return ["memory_z", "memory_x"]
    if config_basis in {"memory_z", "memory_x"}:
        return [config_basis]
    raise ValueError("code.basis must be memory_z, memory_x, or both")


def _per_round_ler(total_ler: float, total_uncertainty: float, rounds: int) -> tuple[float, float]:
    if rounds <= 1:
        return total_ler, total_uncertainty
    clamped = min(max(float(total_ler), 0.0), 0.499999999)
    survival = 1.0 - 2.0 * clamped
    per_round = (1.0 - survival ** (1.0 / rounds)) / 2.0
    derivative = (1.0 / rounds) * survival ** ((1.0 / rounds) - 1.0)
    return float(per_round), float(abs(derivative) * total_uncertainty)
