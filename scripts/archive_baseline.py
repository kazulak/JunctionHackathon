from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


COMPACT_FILES = [
    "sweep_results.csv",
    "sweep_results.json",
    "summary.md",
    "ler_vs_rounds.png",
    "detector_rate_vs_rounds.png",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive a compact sweep summary under baselines/."
    )
    parser.add_argument(
        "sweep_dir",
        type=Path,
        help="Sweep result directory containing sweep_results.csv.",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Folder name to create under baselines/.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Human-readable title for the generated README.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Short note added to the generated README.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("baselines"),
        help="Archive root. Defaults to baselines/.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing archive folder.",
    )
    args = parser.parse_args()

    sweep_dir = args.sweep_dir
    if not (sweep_dir / "sweep_results.csv").exists():
        raise SystemExit(f"Missing sweep_results.csv in {sweep_dir}")

    output_dir = args.output_root / args.name
    if output_dir.exists():
        if not args.force:
            raise SystemExit(f"Archive already exists: {output_dir}. Use --force to overwrite.")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    copied = _copy_compact_files(sweep_dir, output_dir)
    rows = _read_sweep_rows(sweep_dir / "sweep_results.csv")
    hardware_rows = _build_hardware_rows(rows)
    if hardware_rows:
        _write_csv(output_dir / "hardware_metadata.csv", hardware_rows)

    _write_readme(
        output_dir=output_dir,
        title=args.title or args.name,
        source_sweep=sweep_dir,
        rows=rows,
        hardware_rows=hardware_rows,
        copied=copied,
        notes=args.notes,
    )

    print(f"Archived baseline: {output_dir}")
    print(f"README: {output_dir / 'README.md'}")
    if hardware_rows:
        print(f"Hardware metadata: {output_dir / 'hardware_metadata.csv'}")
    return 0


def _copy_compact_files(source: Path, destination: Path) -> list[str]:
    copied = []
    for name in COMPACT_FILES:
        source_path = source / name
        if source_path.exists():
            shutil.copy2(source_path, destination / name)
            copied.append(name)
    return copied


def _read_sweep_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row["rounds"] = int(row["rounds"])
            row["ler"] = _float(row.get("ler"))
            row["uncertainty"] = _float(row.get("uncertainty"))
            row["logical_error_per_round"] = _float_or_none(
                row.get("logical_error_per_round")
            )
            row["logical_error_per_round_uncertainty"] = _float_or_none(
                row.get("logical_error_per_round_uncertainty")
            )
            row["logical_failures"] = _int(row.get("logical_failures"))
            row["shots"] = _int(row.get("shots"))
            row["original_shots"] = _int_or_none(row.get("original_shots"))
            row["kept_shots"] = _int_or_none(row.get("kept_shots"))
            row["postselection_fraction"] = _float_or_none(
                row.get("postselection_fraction")
            )
            row["mean_detector_firing_rate"] = _float_or_none(
                row.get("mean_detector_firing_rate")
            )
            row["max_detector_firing_rate"] = _float_or_none(
                row.get("max_detector_firing_rate")
            )
            row["mean_syndrome_weight"] = _float_or_none(row.get("mean_syndrome_weight"))
            rows.append(row)
    return rows


def _build_hardware_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hardware_rows = []
    for row in rows:
        run_dir = Path(str(row["run_dir"]))
        basis_dir = run_dir / str(row["basis"])
        raw_metadata = _read_json_if_exists(basis_dir / "raw_metadata.json")
        metrics = _read_json_if_exists(basis_dir / "metrics.json")
        if not raw_metadata:
            continue

        transpilation = raw_metadata.get("transpilation_metrics", {}) or {}
        mapping = raw_metadata.get("mapping", {}) or {}
        dd = raw_metadata.get("dynamical_decoupling", {}) or {}
        decoder_info = metrics.get("decoder_info", {}) if metrics else {}

        hardware_rows.append(
            {
                "rounds": row["rounds"],
                "basis": row["basis"],
                "ler": row["ler"],
                "uncertainty": row["uncertainty"],
                "logical_failures": row["logical_failures"],
                "shots": row["shots"],
                "original_shots": row.get("original_shots"),
                "kept_shots": row.get("kept_shots"),
                "postselection_fraction": row.get("postselection_fraction"),
                "mean_detector_firing_rate": row.get("mean_detector_firing_rate"),
                "job_id": raw_metadata.get("job_id"),
                "batch_index": raw_metadata.get("batch_index"),
                "batch_size": raw_metadata.get("batch_size"),
                "quantum_computer": raw_metadata.get("quantum_computer"),
                "qpu": mapping.get("qpu"),
                "qiskit_depth": raw_metadata.get("qiskit_depth"),
                "transpiled_depth": raw_metadata.get("transpiled_depth"),
                "qiskit_two_qubit_gate_count": transpilation.get(
                    "qiskit_two_qubit_gate_count"
                ),
                "transpiled_two_qubit_gate_count": transpilation.get(
                    "transpiled_two_qubit_gate_count"
                ),
                "swap_count": transpilation.get("swap_count"),
                "expected_swap_count_from_mapping": transpilation.get(
                    "expected_swap_count_from_mapping"
                ),
                "native_code_edges": transpilation.get("native_code_edges"),
                "routed_code_edges": transpilation.get("routed_code_edges"),
                "unique_code_edges": transpilation.get("unique_code_edges"),
                "omit_initial_resets": raw_metadata.get("omit_initial_resets"),
                "omit_repeated_resets": raw_metadata.get("omit_repeated_resets"),
                "dynamical_decoupling_enabled": dd.get("enabled"),
                "dynamical_decoupling_applied": dd.get("applied"),
                "dynamical_decoupling_error": dd.get("error"),
                "selected_candidate": decoder_info.get("selected_candidate"),
            }
        )
    return hardware_rows


def _write_readme(
    output_dir: Path,
    title: str,
    source_sweep: Path,
    rows: list[dict[str, Any]],
    hardware_rows: list[dict[str, Any]],
    copied: list[str],
    notes: str,
) -> None:
    lines = [
        f"# {title}",
        "",
        f"- Archived: {_timestamp()}",
        f"- Source sweep: `{source_sweep}`",
    ]
    if notes:
        lines.append(f"- Notes: {notes}")
    lines.extend(["", "## Results", "", _result_table(rows)])

    if hardware_rows:
        lines.extend(["", "## Hardware Metadata", "", _hardware_summary(hardware_rows)])

    lines.extend(["", "## Files", ""])
    for name in copied:
        lines.append(f"- `{name}`")
    if hardware_rows:
        lines.append("- `hardware_metadata.csv`")
    lines.append("- `README.md`")

    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _result_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Rounds | Basis | LER | Uncertainty | Kept/Original | Detector rate | Candidate |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(rows, key=lambda item: (item["rounds"], item["basis"])):
        candidate = _md(_selected_candidate(row))
        original = row.get("original_shots") or row["shots"]
        kept = row.get("kept_shots") or row["shots"]
        lines.append(
            f"| {row['rounds']} | {row['basis']} | {_fmt(row['ler'])} | "
            f"{_fmt(row['uncertainty'])} | {kept}/{original} | "
            f"{_fmt(row.get('mean_detector_firing_rate'))} | {candidate} |"
        )
    return "\n".join(lines)


def _selected_candidate(row: dict[str, Any]) -> str:
    run_dir = Path(str(row["run_dir"]))
    metrics = _read_json_if_exists(run_dir / str(row["basis"]) / "metrics.json")
    decoder_info = metrics.get("decoder_info", {}) if metrics else {}
    return str(decoder_info.get("selected_candidate", ""))


def _hardware_summary(rows: list[dict[str, Any]]) -> str:
    job_ids = sorted({str(row["job_id"]) for row in rows if row.get("job_id")})
    qpus = sorted({str(row["qpu"]) for row in rows if row.get("qpu")})
    max_depth = max(_int_or_none(row.get("transpiled_depth")) or 0 for row in rows)
    max_two_qubit = max(
        _int_or_none(row.get("transpiled_two_qubit_gate_count")) or 0 for row in rows
    )
    max_swaps = max(_int_or_none(row.get("swap_count")) or 0 for row in rows)
    dd_applied = sorted(
        {str(row.get("dynamical_decoupling_applied")) for row in rows if row.get("dynamical_decoupling_enabled")}
    )

    lines = [
        f"- Jobs: {', '.join(job_ids) if job_ids else ''}",
        f"- QPU: {', '.join(qpus) if qpus else ''}",
        f"- Max transpiled depth: {max_depth}",
        f"- Max transpiled two-qubit gates: {max_two_qubit}",
        f"- Max SWAP count: {max_swaps}",
        f"- Dynamical decoupling applied values: {', '.join(dd_applied) if dd_applied else ''}",
        "",
        "Detailed per-basis rows are in `hardware_metadata.csv`.",
    ]
    return "\n".join(lines)


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _float(value: Any) -> float:
    return float(value)


def _float_or_none(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _int(value: Any) -> int:
    return int(float(value))


def _int_or_none(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(float(value))


def _fmt(value: Any) -> str:
    if value in {None, ""}:
        return ""
    return f"{float(value):.6g}"


def _md(value: str) -> str:
    return value.replace("|", "\\|")


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
