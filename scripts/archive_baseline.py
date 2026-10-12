"""Archive a compact summary of a finished sweep under baselines/.

    python scripts/archive_baseline.py results/<sweep>/<timestamp> --name <folder> \\
        --provenance post_hackathon --output-root baselines/post_hackathon --title "<title>"
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.analysis.tables import fmt, read_sweep_csv, wilson_text, write_csv
from qec_pipeline.provenance import uuid7_time

PROVENANCE_LABELS = {
    "hackathon": "Hackathon (Junction Quantum Hack 2026, run before the 2026-06-07 submission)",
    "post_hackathon": "Post-hackathon development (not part of the submission)",
}
COMPACT_FILES = [
    "sweep_results.csv",
    "sweep_results.json",
    "summary.md",
    "ler_vs_rounds.png",
    "detector_rate_vs_rounds.png",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep_dir", type=Path, help="Sweep result directory containing sweep_results.csv.")
    parser.add_argument("--name", required=True, help="Folder name to create under the output root.")
    parser.add_argument("--title", default=None, help="Human-readable title for the generated README.")
    parser.add_argument(
        "--provenance",
        required=True,
        choices=sorted(PROVENANCE_LABELS),
        help="Whether this run belongs to the hackathon submission or later work.",
    )
    parser.add_argument("--notes", default="", help="Short note added to the generated README.")
    parser.add_argument("--output-root", type=Path, default=Path("baselines"), help="Defaults to baselines/.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing archive folder.")
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

    copied = []
    for name in COMPACT_FILES:
        if (sweep_dir / name).exists():
            shutil.copy2(sweep_dir / name, output_dir / name)
            copied.append(name)
    rows = read_sweep_csv(sweep_dir / "sweep_results.csv")
    hardware_rows = _hardware_rows(rows)
    write_csv(output_dir / "hardware_metadata.csv", hardware_rows)
    _write_readme(
        output_dir, args.title or args.name, sweep_dir, rows, hardware_rows, copied, args.notes, args.provenance
    )

    print(f"Archived baseline: {output_dir}")
    print(f"README: {output_dir / 'README.md'}")
    if hardware_rows:
        print(f"Hardware metadata: {output_dir / 'hardware_metadata.csv'}")
    return 0


def _hardware_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per hardware basis run (simulator runs have no job id and are skipped)."""
    hardware_rows = []
    for row in rows:
        basis_dir = Path(str(row["run_dir"])) / str(row["basis"])
        raw = _read_json(basis_dir / "raw_metadata.json")
        if not raw.get("job_id"):
            continue
        transpilation = raw.get("transpilation_metrics") or {}
        mapping = raw.get("mapping") or {}
        loci = raw.get("physical_loci") or {}
        compile_options = raw.get("compilation_options") or {}
        # June 2026 runs recorded a client-side DD attempt here; newer runs use IQM's native DD option.
        legacy_dd = raw.get("dynamical_decoupling") or {}
        decoder_info = _read_json(basis_dir / "metrics.json").get("decoder_info", {})
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
                "job_id": raw.get("job_id"),
                "job_submitted_utc": _job_time(raw.get("job_id")),
                "batch_index": raw.get("batch_index"),
                "batch_size": raw.get("batch_size"),
                "quantum_computer": raw.get("quantum_computer"),
                "qpu": mapping.get("qpu"),
                "qiskit_depth": raw.get("qiskit_depth"),
                "transpiled_depth": raw.get("transpiled_depth"),
                "qiskit_two_qubit_gate_count": transpilation.get("qiskit_two_qubit_gate_count"),
                "transpiled_two_qubit_gate_count": transpilation.get("transpiled_two_qubit_gate_count"),
                "swap_count": transpilation.get("swap_count"),
                "expected_swap_count_from_mapping": transpilation.get("expected_swap_count_from_mapping"),
                "native_code_edges": transpilation.get("native_code_edges"),
                "routed_code_edges": transpilation.get("routed_code_edges"),
                "unique_code_edges": transpilation.get("unique_code_edges"),
                "omit_initial_resets": raw.get("omit_initial_resets"),
                "mid_circuit_reset": raw.get("mid_circuit_reset"),
                "dynamical_decoupling_enabled": legacy_dd.get("enabled", compile_options.get("dynamical_decoupling")),
                "dynamical_decoupling_applied": legacy_dd.get("applied"),
                "dynamical_decoupling_error": legacy_dd.get("error"),
                "active_reset_cycles": compile_options.get("active_reset_cycles"),
                "calibration_set_id": raw.get("calibration_set_id"),
                "shot_order_preserved": raw.get("shot_order_preserved"),
                "physical_qubits": " ".join(loci.get("physical_qubits", [])) or None,
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
    provenance: str,
) -> None:
    lines = [
        f"# {title}",
        "",
        f"- Provenance: **{PROVENANCE_LABELS[provenance]}**",
        f"- Archived: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}",
        f"- Source sweep: `{source_sweep}`",
    ]
    source_provenance = _read_json(source_sweep / "sweep_results.json").get("provenance")
    if source_provenance:
        commit = (source_provenance.get("git_commit") or "unknown")[:7]
        dirty = " (uncommitted changes)" if source_provenance.get("git_dirty") else ""
        lines.append(f"- Code that produced the sweep: `{commit}`{dirty}")
    if notes:
        lines.append(f"- Notes: {notes}")

    lines += [
        "",
        "## Results",
        "",
        "| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(rows, key=lambda item: (item["rounds"], item["basis"])):
        metrics = _read_json(Path(str(row["run_dir"])) / str(row["basis"]) / "metrics.json")
        candidate = str(metrics.get("decoder_info", {}).get("selected_candidate", "")).replace("|", "\\|")
        lines.append(
            f"| {row['rounds']} | {row['basis']} | {fmt(row['ler'], 6)} | "
            f"{wilson_text(row['logical_failures'], row['shots'])} | "
            f"{row.get('kept_shots') or row['shots']}/{row.get('original_shots') or row['shots']} | "
            f"{fmt(row.get('mean_detector_firing_rate'), 6)} | {candidate} |"
        )

    if hardware_rows:
        lines += ["", "## Hardware Metadata", "", _hardware_summary(hardware_rows)]
    lines += ["", "## Files", ""]
    lines += [f"- `{name}`" for name in copied]
    if hardware_rows:
        lines.append("- `hardware_metadata.csv`")
    lines.append("- `README.md`")
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hardware_summary(rows: list[dict[str, Any]]) -> str:
    def values(key: str) -> str:
        return ", ".join(sorted({str(row[key]) for row in rows if row.get(key) not in {None, ""}}))

    def largest(key: str) -> int:
        return max(int(row.get(key) or 0) for row in rows)

    jobs = sorted({f"{row['job_id']} (submitted {row.get('job_submitted_utc')} UTC)" for row in rows})
    return "\n".join(
        [
            f"- Jobs: {', '.join(jobs)}",
            f"- QPU: {values('qpu')}",
            f"- Max transpiled depth: {largest('transpiled_depth')}",
            f"- Max transpiled two-qubit gates: {largest('transpiled_two_qubit_gate_count')}",
            f"- Max SWAP count: {largest('swap_count')}",
            f"- Dynamical decoupling requested: {values('dynamical_decoupling_enabled')}",
            f"- Active reset cycles between shots: {values('active_reset_cycles') or 'none (passive reset)'}",
            "",
            "Detailed per-basis rows are in `hardware_metadata.csv`.",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _job_time(job_id: Any) -> str | None:
    if not job_id:
        return None
    try:
        return uuid7_time(str(job_id)).isoformat(timespec="seconds")
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
