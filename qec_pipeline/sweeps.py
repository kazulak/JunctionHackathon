from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from qec_pipeline.analysis.metrics import fit_per_round_error
from qec_pipeline.analysis.reports import write_run_artifacts, write_run_summary
from qec_pipeline.artifacts import prepare_run_directory, utc_timestamp
from qec_pipeline.backends.iqm_hardware import run_iqm_hardware_batch_backend
from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.codes import get_code_builder
from qec_pipeline.decoders import get_decoder
from qec_pipeline.mapping import active_stim_to_dense, select_mapping_from_config
from qec_pipeline.pipeline import basis_list, build_basis_metrics, is_memory_experiment, run_pipeline
from qec_pipeline.provenance import provenance_line, run_provenance
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
    """Run one pipeline job per round value and write CSV/JSON/plot summary.

    The qubit layout is selected once and pinned for every round value, so an
    LER-vs-rounds curve never mixes different physical patches.
    """
    base_config = pin_sweep_mapping(base_config)
    if _use_iqm_batch_sweep(base_config):
        return _run_iqm_rounds_sweep_batch(base_config, rounds, output_root)

    base_name = base_config["experiment"]["name"]
    timestamp = utc_timestamp()
    root = output_root or Path(base_config["artifacts"].get("root", "results"))
    sweep_dir = root / f"{base_name}_rounds_sweep" / timestamp
    runs_root = sweep_dir / "runs"
    sweep_dir.mkdir(parents=True, exist_ok=False)

    rows = []
    layouts = []
    for rounds_value in rounds:
        config = copy.deepcopy(base_config)
        config["code"]["rounds"] = int(rounds_value)
        config["experiment"]["name"] = f"{base_name}_rounds_{rounds_value}"
        config["artifacts"]["root"] = str(runs_root)

        run_dir, basis_results, notes = run_pipeline(config)
        for _basis, circuit, _raw, _syndromes, _decoded, metrics in basis_results:
            layouts.append(_layout_of(circuit))
            rows.append(_sweep_row(int(rounds_value), metrics, run_dir, notes))

    _check_single_layout(layouts)
    _write_sweep_outputs(sweep_dir, base_config, rounds, rows)
    return sweep_dir


def pin_sweep_mapping(base_config: dict[str, Any]) -> dict[str, Any]:
    """Return a config whose mapping is a fixed Stim-to-hardware assignment.

    Configs that already pin `mapping.hardware_patch.stim_to_hardware`, or use no
    mapping, are returned unchanged.
    """
    mapping = base_config.get("mapping") or {}
    if mapping.get("strategy", "none") in {"none", None}:
        return base_config
    if (mapping.get("hardware_patch") or {}).get("stim_to_hardware"):
        return base_config

    config = copy.deepcopy(base_config)
    code = dict(config["code"])
    basis = basis_list(code["basis"])[0]
    stim_circuit = get_code_builder(code.get("family", "surface_code"))(
        code,
        {"model": "no_noise", "parameters": {}},
        basis,
    )[0]
    selected = select_mapping_from_config(config["mapping"], stim_circuit, active_stim_to_dense(stim_circuit))
    config["mapping"]["hardware_patch"] = {"stim_to_hardware": selected["stim_to_hardware"]}
    config["mapping"]["pinned_from_strategy"] = mapping.get("strategy")
    if selected.get("strategy") == "calibration_routed_layout" or selected.get("routed_code_edges"):
        options = dict(config["mapping"].get("options") or {})
        options["allow_routing"] = True
        config["mapping"]["options"] = options
    return config


def _layout_of(circuit: tuple) -> tuple | None:
    mapping = circuit[3].get("mapping") or {}
    stim_to_hardware = mapping.get("stim_to_hardware")
    return tuple(sorted(stim_to_hardware.items())) if stim_to_hardware else None


def _check_single_layout(layouts: list[tuple | None]) -> None:
    distinct = {layout for layout in layouts if layout is not None}
    if len(distinct) > 1:
        raise RuntimeError(f"Sweep used {len(distinct)} different qubit layouts; expected one.")


def _run_iqm_rounds_sweep_batch(
    base_config: dict[str, Any],
    rounds: list[int],
    output_root: Path | None = None,
) -> Path:
    """Submit all IQM sweep circuits in one batch before waiting for results."""
    base_name = base_config["experiment"]["name"]
    timestamp = utc_timestamp()
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

        for basis in basis_list(config["code"]["basis"]):
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

    _check_single_layout([_layout_of(job["circuit"]) for job in jobs])
    raws = run_iqm_hardware_batch_backend(
        base_config["backend"],
        [
            {"circuit": job["circuit"], "mapping": job["mapping"]}
            for job in jobs
        ],
    )

    rows = []
    for job, raw in zip(jobs, raws, strict=True):
        group = job["group"]
        basis = job["basis"]
        circuit = job["circuit"]
        syndromes = extract_detection_events(circuit, raw)
        _detection_events, _observable_flips, syndrome_info = syndromes
        decoded = get_decoder(job["decoder"]["name"])(job["decoder"], circuit, syndromes)
        _predicted, _failures, ler, uncertainty, _decoder_info = decoded
        metrics = build_basis_metrics(
            basis,
            group["rounds"],
            decoded,
            syndrome_info,
            memory_experiment=is_memory_experiment(circuit),
        )

        basis_run_dir = group["run_dir"] / basis
        basis_run_dir.mkdir(parents=True, exist_ok=False)
        write_run_artifacts(
            basis_run_dir,
            circuit,
            raw,
            syndromes,
            metrics,
            group["config"]["artifacts"],
        )

        group["basis_results"].append((basis, circuit, raw, syndromes, decoded, metrics))
        note = f"{basis}: LER {ler} +/- {uncertainty}"
        group["notes"].append(note)
        rows.append(_sweep_row(group["rounds"], metrics, group["run_dir"], group["notes"]))

    for group in groups:
        write_run_summary(
            group["run_dir"],
            group["config"],
            group["basis_results"],
            group["notes"],
        )

    _write_sweep_outputs(sweep_dir, base_config, rounds, rows)
    return sweep_dir


def _sweep_row(
    rounds: int,
    metrics: dict[str, Any],
    run_dir: Path,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "rounds": int(rounds),
        "basis": metrics["basis"],
        "ler": float(metrics["ler"]),
        "uncertainty": float(metrics["uncertainty"]),
        "ler_ci_low": metrics.get("ler_ci_low"),
        "ler_ci_high": metrics.get("ler_ci_high"),
        "logical_error_per_round": metrics.get("logical_error_per_round"),
        "logical_error_per_round_uncertainty": metrics.get("logical_error_per_round_uncertainty"),
        "logical_failures": int(metrics["logical_failures"]),
        "shots": int(metrics["shots"]),
        "mean_detector_firing_rate": metrics.get("mean_detector_firing_rate"),
        "max_detector_firing_rate": metrics.get("max_detector_firing_rate"),
        "mean_syndrome_weight": metrics.get("mean_syndrome_weight"),
        "original_shots": metrics.get("original_shots", metrics["shots"]),
        "kept_shots": metrics.get("kept_shots", metrics["shots"]),
        "postselection_fraction": metrics.get("postselection_fraction", 1.0),
        "selection_is_in_sample": bool(metrics.get("selection_is_in_sample", False)),
        "memory_experiment": bool(metrics.get("memory_experiment", True)),
        "run_dir": str(run_dir),
        "notes": "; ".join(notes),
    }


def _write_sweep_outputs(
    sweep_dir: Path,
    base_config: dict[str, Any],
    rounds: list[int],
    rows: list[dict[str, Any]],
) -> None:
    provenance = run_provenance()
    fits = _fit_by_basis(rows)
    csv_path = sweep_dir / "sweep_results.csv"
    fieldnames = [
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
        "memory_experiment",
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
                "config_path": base_config.get("_config_path"),
                "provenance": provenance,
                "rounds": rounds,
                "rows": rows,
                "per_round_fits": fits,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    plot_path = sweep_dir / "ler_vs_rounds.png"
    plot_ler_vs_rounds(rows, plot_path)
    detector_plot_path = sweep_dir / "detector_rate_vs_rounds.png"
    plot_detector_rate_vs_rounds(rows, detector_plot_path)

    summary_lines = [
        f"# Rounds Sweep: {base_config['experiment']['name']}",
        "",
        provenance_line(provenance),
        f"- Config: `{base_config.get('_config_path', 'unknown')}`",
        f"- Rounds: {rounds}",
        f"- Results CSV: `{csv_path.name}`",
        f"- Results JSON: `{json_path.name}`",
        f"- Plot: `{plot_path.name}`",
        f"- Detector-rate plot: `{detector_plot_path.name}`",
        "",
        "## Results",
        "",
        "LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.",
        "",
        "| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original "
        "| Failures | Shots | Selection |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        summary_lines.append(
            f"| {row['rounds']} | {row['basis']} | {_fmt(row['ler'])} | "
            f"{_fmt(row.get('ler_ci_low'))}–{_fmt(row.get('ler_ci_high'))} | "
            f"{_fmt(row.get('logical_error_per_round'))} | "
            f"{_fmt(row.get('mean_detector_firing_rate'))} | "
            f"{row['kept_shots']}/{row['original_shots']} | "
            f"{row['logical_failures']} | {row['shots']} | "
            f"{'in-sample (optimistic)' if row.get('selection_is_in_sample') else 'fixed / out-of-sample'} |"
        )
    summary_lines.extend(
        [
            "",
            "## Per-round fit",
            "",
            "Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.",
            "",
            "| Basis | Fit points | Error per round | 1-sigma | Amplitude A |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for basis, fit in fits.items():
        summary_lines.append(
            f"| {basis} | {fit['fit_points']} | {_fmt(fit['fitted_logical_error_per_round'])} | "
            f"{_fmt(fit['fitted_logical_error_per_round_uncertainty'])} | {_fmt(fit['fit_amplitude'])} |"
        )
    (sweep_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def _fit_by_basis(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        basis: fit_per_round_error([row for row in rows if row["basis"] == basis])
        for basis in sorted({row["basis"] for row in rows})
    }


def _fmt(value: Any) -> str:
    if value in {None, ""}:
        return ""
    return f"{float(value):.4g}"


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


def plot_detector_rate_vs_rounds(rows: list[dict[str, Any]], output_path: Path) -> None:
    """Plot mean detector firing probability against rounds, one line per basis."""
    rows_with_rates = [
        row for row in rows if row.get("mean_detector_firing_rate") not in {None, ""}
    ]
    if not rows_with_rates:
        return

    bases = sorted({row["basis"] for row in rows_with_rates})
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for basis in bases:
        basis_rows = sorted(
            [row for row in rows_with_rates if row["basis"] == basis],
            key=lambda row: row["rounds"],
        )
        xs = [row["rounds"] for row in basis_rows]
        ys = [float(row["mean_detector_firing_rate"]) for row in basis_rows]
        ax.plot(xs, ys, marker="o", label=basis)

    ax.set_xlabel("Rounds")
    ax.set_ylabel("Mean detector firing rate")
    ax.set_title("Detector rate vs rounds")
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

