from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "judge_results"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)

    surface_hw = _latest(ROOT / "results" / "sweep_d3_best_iqm_rounds_sweep")
    surface_sim = _latest(ROOT / "results" / "sweep_d3_best_sim_rounds_sweep")
    rep_hw = _latest(ROOT / "results" / "final_rep_code_iqm_rounds_sweep")
    rep_sim = _latest(ROOT / "results" / "final_rep_code_sim_rounds_sweep")

    surface_rows = _read_sweep(surface_hw / "sweep_results.csv")
    surface_sim_rows = _read_sweep(surface_sim / "sweep_results.csv") if surface_sim else []
    rep_hw_rows = _read_sweep(rep_hw / "sweep_results.csv")
    rep_sim_rows = _read_sweep(rep_sim / "sweep_results.csv") if rep_sim else []

    _copy(surface_hw / "sweep_results.csv", OUT / "tables" / "surface_code_hardware.csv")
    if surface_sim:
        _copy(surface_sim / "sweep_results.csv", OUT / "tables" / "surface_code_simulator.csv")
    _copy(rep_hw / "sweep_results.csv", OUT / "tables" / "repetition_code_hardware_garnet.csv")
    if rep_sim:
        _copy(rep_sim / "sweep_results.csv", OUT / "tables" / "repetition_code_simulator.csv")

    _write_per_round_table(rep_hw_rows, OUT / "tables" / "repetition_code_hardware_per_round.csv")
    _write_swap_summary(
        [
            ("surface_code_hardware", surface_hw),
            ("repetition_code_hardware_garnet", rep_hw),
        ],
        OUT / "tables" / "swap_depth_summary.csv",
    )
    _write_plots(surface_rows, surface_sim_rows, rep_hw_rows, rep_sim_rows)
    _write_readme(surface_hw, surface_sim, rep_hw, rep_sim, surface_rows, rep_hw_rows)
    _write_one_pager(surface_hw, surface_sim, rep_hw, rep_sim, surface_rows, rep_hw_rows)
    _write_demo_script()
    _write_judging_matrix()

    print(f"Judge pack written to: {OUT}")


def _latest(path: Path) -> Path | None:
    if not path.exists():
        return None
    dirs = [item for item in path.iterdir() if item.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda item: item.stat().st_mtime)


def _read_sweep(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _copy(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copy2(src, dst)


def _write_per_round_table(rows: list[dict[str, str]], path: Path) -> None:
    fieldnames = [
        "rounds",
        "basis",
        "total_ler",
        "total_uncertainty",
        "per_round_ler",
        "per_round_uncertainty",
        "shots",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            rounds = int(row["rounds"])
            ler = float(row["ler"])
            uncertainty = float(row["uncertainty"])
            per_round, per_round_uncertainty = _per_round_ler(ler, uncertainty, rounds)
            writer.writerow(
                {
                    "rounds": rounds,
                    "basis": row["basis"],
                    "total_ler": ler,
                    "total_uncertainty": uncertainty,
                    "per_round_ler": per_round,
                    "per_round_uncertainty": per_round_uncertainty,
                    "shots": row["shots"],
                }
            )


def _write_swap_summary(experiments: list[tuple[str, Path | None]], path: Path) -> None:
    fieldnames = [
        "experiment",
        "rounds",
        "basis",
        "quantum_computer",
        "qiskit_depth",
        "transpiled_depth",
        "qiskit_two_qubit",
        "transpiled_two_qubit",
        "added_two_qubit",
        "swap_count",
        "native_code_edges",
        "routed_code_edges",
        "expected_swap_count_from_mapping",
        "job_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for experiment, sweep_dir in experiments:
            if sweep_dir is None:
                continue
            for raw_path in sorted(sweep_dir.glob("runs/*/*/*/raw_metadata.json")):
                basis_dir = raw_path.parent
                raw = _json(raw_path)
                circuit = _json(basis_dir / "circuit_metadata.json")
                qiskit_ops = raw.get("qiskit_ops", {})
                transpiled_ops = raw.get("transpiled_ops", {})
                q2 = _two_qubit_count(qiskit_ops)
                t2 = _two_qubit_count(transpiled_ops)
                mapping = raw.get("mapping") or circuit.get("mapping") or {}
                writer.writerow(
                    {
                        "experiment": experiment,
                        "rounds": circuit.get("rounds"),
                        "basis": circuit.get("basis"),
                        "quantum_computer": raw.get("quantum_computer"),
                        "qiskit_depth": raw.get("qiskit_depth"),
                        "transpiled_depth": raw.get("transpiled_depth"),
                        "qiskit_two_qubit": q2,
                        "transpiled_two_qubit": t2,
                        "added_two_qubit": t2 - q2,
                        "swap_count": int(transpiled_ops.get("swap", 0)),
                        "native_code_edges": mapping.get("native_code_edges"),
                        "routed_code_edges": mapping.get("routed_code_edges"),
                        "expected_swap_count_from_mapping": mapping.get("expected_swap_count"),
                        "job_id": raw.get("job_id"),
                    }
                )


def _write_plots(
    surface_rows: list[dict[str, str]],
    surface_sim_rows: list[dict[str, str]],
    rep_hw_rows: list[dict[str, str]],
    rep_sim_rows: list[dict[str, str]],
) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7.0, 4.2))
    _plot_rows(surface_sim_rows, "surface code simulator", marker="o", linestyle="--")
    _plot_rows(surface_rows, "surface code hardware", marker="o", linestyle="-")
    _plot_rows(rep_hw_rows, "repetition code hardware", marker="s", linestyle="-")
    if rep_sim_rows:
        _plot_rows(rep_sim_rows, "repetition code simulator", marker="^", linestyle="--")
    plt.axhline(0.5, color="gray", linestyle="--", linewidth=1, label="random LER")
    plt.xlabel("rounds")
    plt.ylabel("logical error rate")
    plt.title("LER vs rounds")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "plots" / "ler_vs_rounds_combined.png", dpi=160)
    plt.close()

    per_round_rows = []
    for row in rep_hw_rows:
        rounds = int(row["rounds"])
        ler = float(row["ler"])
        uncertainty = float(row["uncertainty"])
        per_round, per_round_uncertainty = _per_round_ler(ler, uncertainty, rounds)
        per_round_rows.append((rounds, per_round, per_round_uncertainty))

    plt.figure(figsize=(7.0, 4.2))
    plt.errorbar(
        [item[0] for item in per_round_rows],
        [item[1] for item in per_round_rows],
        yerr=[item[2] for item in per_round_rows],
        marker="o",
        capsize=3,
    )
    plt.xlabel("rounds")
    plt.ylabel("logical error per round")
    plt.title("Repetition-code per-round logical error on Garnet")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "plots" / "rep_code_per_round_ler.png", dpi=160)
    plt.close()


def _plot_rows(rows: list[dict[str, str]], label: str, marker: str, linestyle: str) -> None:
    import matplotlib.pyplot as plt

    if not rows:
        return
    by_basis: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_basis.setdefault(row.get("basis", "all"), []).append(row)
    show_basis = len(by_basis) > 1
    for basis, basis_rows in sorted(by_basis.items()):
        ordered = sorted(basis_rows, key=lambda row: int(row["rounds"]))
        xs = [int(row["rounds"]) for row in ordered]
        ys = [float(row["ler"]) for row in ordered]
        yerr = [float(row["uncertainty"]) for row in ordered]
        series_label = f"{label} {basis}" if show_basis else label
        plt.errorbar(xs, ys, yerr=yerr, marker=marker, linestyle=linestyle, capsize=3, label=series_label)


def _write_readme(
    surface_hw: Path | None,
    surface_sim: Path | None,
    rep_hw: Path | None,
    rep_sim: Path | None,
    surface_rows: list[dict[str, str]],
    rep_hw_rows: list[dict[str, str]],
) -> None:
    best_rep = min(rep_hw_rows, key=lambda row: float(row["ler"]))
    long_rep = max(rep_hw_rows, key=lambda row: int(row["rounds"]))
    per_round, per_round_unc = _per_round_ler(
        float(long_rep["ler"]),
        float(long_rep["uncertainty"]),
        int(long_rep["rounds"]),
    )
    surface_r3 = next((row for row in surface_rows if int(row["rounds"]) == 3), None)

    lines = [
        "# Judge Results",
        "",
        "This folder is a curated subset of the full `results/` tree.",
        "",
        "## Headline",
        "",
        "- Surface-code pipeline is functional but saturates on hardware from round 3.",
        "- Surface-code simulator degrades gradually, showing the hardware gap clearly.",
        "- Repetition-code module is a final hardware-optimized path using only 5 qubits.",
        "- Garnet repetition-code hardware reaches low total LER even at long rounds.",
        "",
        "## Key Numbers",
        "",
        f"- Surface-code hardware artifact: `{_rel(surface_hw)}`",
        f"- Surface-code simulator artifact: `{_rel(surface_sim)}`",
        f"- Repetition-code hardware artifact: `{_rel(rep_hw)}`",
        f"- Repetition-code simulator artifact: `{_rel(rep_sim)}`",
        "",
    ]
    if surface_r3:
        lines.append(
            "- Surface code r=3 hardware LER: "
            f"{float(surface_r3['ler']):.4f} +/- {float(surface_r3['uncertainty']):.4f}"
        )
    lines.extend(
        [
            "- Best repetition-code hardware LER: "
            f"r={best_rep['rounds']} total {float(best_rep['ler']):.4f} "
            f"+/- {float(best_rep['uncertainty']):.4f}",
            "- Long repetition-code hardware LER: "
            f"r={long_rep['rounds']} total {float(long_rep['ler']):.4f} "
            f"+/- {float(long_rep['uncertainty']):.4f}",
            "- Long repetition-code per-round LER: "
            f"{per_round:.6f} +/- {per_round_unc:.6f}",
            "- Literal transpiled `swap` gates: 0 in the curated hardware sweeps.",
            "- Long repetition-code r=50 routing overhead: 219 transpiled two-qubit gates vs 200 logical two-qubit gates, so +19 two-qubit gates.",
            "",
            "## Files",
            "",
            "- `FINAL_ONE_PAGER.md`: shortest judge-facing project summary.",
            "- `DEMO_SCRIPT.md`: two-minute presentation script.",
            "- `JUDGING_MATRIX.md`: direct mapping to the challenge judging criteria.",
            "- `plots/ler_vs_rounds_combined.png`: surface simulator/hardware vs repetition-code simulator/hardware.",
            "- `plots/rep_code_per_round_ler.png`: per-round logical error for long memory runs.",
            "- `tables/surface_code_simulator.csv`: surface-code simulator data.",
            "- `tables/swap_depth_summary.csv`: SWAP/depth/two-qubit-gate evidence.",
            "- `tables/repetition_code_hardware_per_round.csv`: total and per-round LER.",
            "",
            "## Judging Criteria Mapping",
            "",
            "- Theoretical correctness: Stim generates detectors/observables; PyMatching decodes detector events; artifacts include raw measurements and detector events.",
            "- Sophistication: hardware-specific fixed layout, batch IQM submission, calibrated noise, explicit SWAP/depth summaries.",
            "- LER statistics: all reported LER values include binomial uncertainties and shot counts.",
            "- Flexibility: surface code, repetition code, simulator, IQM hardware, calibration-driven mapping/noise, postselection decoder route.",
            "",
            "## Caveat",
            "",
            "The repetition code protects one error channel, not full surface-code logical memory. We present it as a hardware-optimized QEC demonstration after identifying that full surface-code rounds saturate on current hardware.",
            "",
            "The fitted simulator curve uses scaled Garnet calibration errors. The first-principles calibration-to-Stim model was too pessimistic for this shallow repetition-code run.",
            "",
            "The fresh hardware curve is non-monotonic after round 26. We report it as measured and treat it as evidence of hardware/batch/reset dynamics, not as a monotonic threshold claim.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_one_pager(
    surface_hw: Path | None,
    surface_sim: Path | None,
    rep_hw: Path | None,
    rep_sim: Path | None,
    surface_rows: list[dict[str, str]],
    rep_hw_rows: list[dict[str, str]],
) -> None:
    best_rep = min(rep_hw_rows, key=lambda row: float(row["ler"]))
    long_rep = max(rep_hw_rows, key=lambda row: int(row["rounds"]))
    per_round, per_round_unc = _per_round_ler(
        float(long_rep["ler"]),
        float(long_rep["uncertainty"]),
        int(long_rep["rounds"]),
    )
    surface_r1 = next((row for row in surface_rows if int(row["rounds"]) == 1), None)
    surface_r3 = next((row for row in surface_rows if int(row["rounds"]) == 3), None)

    lines = [
        "# Final Judge One-Pager",
        "",
        "## Claim",
        "",
        "We built a modular QEC experiment pipeline that can run the same YAML-defined job through Stim simulation or IQM hardware, decode detector events, and produce LER statistics with artifacts.",
        "",
        "The full rotated surface-code path is functional, but repeated hardware rounds saturate near random LER. Our final low-depth improvement is a repetition-code route on Garnet, presented honestly as a one-channel QEC demonstration rather than full surface-code memory.",
        "",
        "## Pipeline",
        "",
        "```text",
        "YAML config",
        "-> code module: surface_code / surface_code_iqm / repetition_code",
        "-> backend: Stim noisy simulator / IQM hardware",
        "-> detector events from Stim detector model",
        "-> decoder: PyMatching / calibrated MWPM / auto weight search",
        "-> LER, uncertainty, raw measurements, syndrome data, plots",
        "```",
        "",
        "## Best Evidence",
        "",
        "| Experiment | Rounds | LER | Evidence |",
        "| --- | ---: | ---: | --- |",
    ]
    if surface_r1:
        lines.append(
            f"| Surface code on IQM hardware | 1 | {float(surface_r1['ler']):.4f} +/- {float(surface_r1['uncertainty']):.4f} | surface path works before repeated-round saturation |"
        )
    if surface_r3:
        lines.append(
            f"| Surface code on IQM hardware | 3 | {float(surface_r3['ler']):.4f} +/- {float(surface_r3['uncertainty']):.4f} | identifies hardware repeated-round failure mode |"
        )
    lines.extend(
        [
            f"| Repetition code on IQM Garnet | {best_rep['rounds']} | {float(best_rep['ler']):.4f} +/- {float(best_rep['uncertainty']):.4f} | best total LER |",
            f"| Repetition code on IQM Garnet | {long_rep['rounds']} | {float(long_rep['ler']):.4f} +/- {float(long_rep['uncertainty']):.4f} | long memory run |",
            f"| Repetition code per-round LER | {long_rep['rounds']} | {per_round:.6f} +/- {per_round_unc:.6f} | converted from total survival model |",
            "",
            "## Hardware-Aware Work",
            "",
            "- Real IQM calibration dumps drive patch selection and calibrated simulator noise.",
            "- IQM sweeps use batch submission so all circuits are queued before waiting.",
            "- Hardware metadata records depth, operation counts, job IDs, selected mapping, and SWAP/routing evidence.",
            "- Curated runs show 0 literal transpiled `swap` gates; the long repetition-code run adds 19 two-qubit gates after routing.",
            "- Experimental hooks exist for postselection, calibrated decoder weights, dynamical decoupling, and alternative code/decoder modules.",
            "",
            "## What We Tried",
            "",
            "- Distance-3 and distance-5 rotated surface-code memory.",
            "- Memory-Z and memory-X basis runs.",
            "- Emerald and Garnet calibration/hardware paths.",
            "- Calibrated noisy Stim simulation from per-qubit and per-coupler data.",
            "- Decoder weight sweeps and low-syndrome postselection.",
            "- Final low-depth repetition-code module distilled from teammate code.",
            "",
            "## What We Did Not Claim",
            "",
            "- The repetition code is not full surface-code logical memory; it protects one error channel.",
            "- NVIDIA Ising, GNN decoding, color code, and PulLA pulse compilation were evaluated as next routes, but not completed in the final runnable evidence path.",
            "- The fitted simulator is useful for rapid iteration, but the first-principles Stim noise model still misses repeated reset/readout, leakage, crosstalk, and pulse-level effects.",
            "",
            "## Artifacts",
            "",
            f"- Surface hardware: `{_rel(surface_hw)}`",
            f"- Surface simulator: `{_rel(surface_sim)}`",
            f"- Repetition hardware: `{_rel(rep_hw)}`",
            f"- Repetition simulator: `{_rel(rep_sim)}`",
            "- Plots: `judge_results/plots/`",
            "- Tables: `judge_results/tables/`",
        ]
    )
    (OUT / "FINAL_ONE_PAGER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_demo_script() -> None:
    lines = [
        "# Two-Minute Demo Script",
        "",
        "## 0:00-0:20: Goal",
        "",
        "Show the YAML-driven QEC pipeline and the final LER evidence. The key point is that the same structure runs simulator and IQM hardware, then writes raw artifacts and plots.",
        "",
        "## 0:20-0:45: Pipeline",
        "",
        "Open `README.md` and show:",
        "",
        "```text",
        "YAML -> Stim circuit -> simulator/IQM -> detector events -> decoder -> LER",
        "```",
        "",
        "Then open `configs/final_rep_code_iqm.yaml` and point at `code.family`, `backend.name`, `decoder.name`, and `mapping.hardware_patch`.",
        "",
        "## 0:45-1:15: Evidence",
        "",
        "Open `judge_results/plots/ler_vs_rounds_combined.png`.",
        "",
        "Say:",
        "",
        "```text",
        "Surface code is functional, but repeated hardware rounds saturate near 0.5 LER.",
        "The final low-depth repetition-code path avoids that saturation on Garnet.",
        "For 50 rounds we measured total LER 0.0163 +/- 0.0009.",
        "Converted per round, that is 0.000331 +/- 0.000018.",
        "```",
        "",
        "## 1:15-1:40: Hardware-Aware Part",
        "",
        "Open `judge_results/tables/swap_depth_summary.csv`.",
        "",
        "Say:",
        "",
        "```text",
        "We record job IDs, depth, two-qubit counts, selected mapping, and SWAP evidence.",
        "Curated hardware runs have 0 literal transpiled SWAP gates.",
        "The long repetition-code run has 219 transpiled two-qubit gates versus 200 logical two-qubit gates.",
        "```",
        "",
        "## 1:40-2:00: Honest Caveat",
        "",
        "Say:",
        "",
        "```text",
        "The repetition code protects one channel, not full surface-code memory.",
        "The important engineering result is the modular pipeline plus the diagnosis:",
        "full surface-code rounds currently fail because the hardware effects are not captured by the simple Stim noise model.",
        "Next steps are PulLA/DD compilation, better reset/readout/leakage noise, and calibrated decoder weights.",
        "```",
        "",
        "## Commands",
        "",
        "Regenerate this judge pack:",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe scripts\\build_judge_pack.py",
        "```",
        "",
        "Run the final simulator/hardware pair:",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe scripts\\sweep_rounds.py configs\\final_rep_code_sim.yaml --rounds 1 50 7",
        ".\\.venv\\Scripts\\python.exe scripts\\sweep_rounds.py configs\\final_rep_code_iqm.yaml --rounds 1 50 7",
        "```",
    ]
    (OUT / "DEMO_SCRIPT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_judging_matrix() -> None:
    lines = [
        "# Judging Matrix",
        "",
        "| Criterion | What to show | Evidence |",
        "| --- | --- | --- |",
        "| Theoretical correctness, 40% | Stim-defined detectors/observables, PyMatching decoding, no-noise sanity, raw detector artifacts | `qec_pipeline/codes/`, `qec_pipeline/decoders/`, `docs/REPETITION_CODE_EXPLANATION.md`, run artifacts |",
        "| Sophistication, 20% | Calibration-driven layouts, fixed Garnet patch, batch IQM submission, SWAP/depth accounting | `qec_pipeline/mapping/`, `qec_pipeline/backends/iqm_hardware.py`, `judge_results/tables/swap_depth_summary.csv` |",
        "| LER statistics, 20% | Round sweeps, binomial uncertainty, shot counts, total and per-round LER | `judge_results/plots/`, `judge_results/tables/` |",
        "| Flexibility and advanced functionality, 20% | YAML-swappable code/backend/decoder/noise modules, calibrated noise, postselection route, DD hook, future Ising/GNN/color-code slots | `configs/`, `docs/MODULE_INTEGRATION.md`, `docs/JUDGE_SUMMARY.md` |",
        "| Bonus: hardware flexibility | Emerald and Garnet calibration files; configs can switch QPU/backend while preserving pipeline shape | `configs/2026-06-06T06_08_52.470451Z.json`, `configs/2026-06-06T16_44_10.718568Z.json` |",
        "| Bonus: diagnosis | Identified repeated-round hardware saturation as the main blocker, separate from one-round correctness | `docs/JUDGE_SUMMARY.md`, `judge_results/README.md` |",
    ]
    (OUT / "JUDGING_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _per_round_ler(total_ler: float, total_uncertainty: float, rounds: int) -> tuple[float, float]:
    if rounds <= 1:
        return total_ler, total_uncertainty
    clamped = min(max(total_ler, 0.0), 0.499999999)
    survival = 1.0 - 2.0 * clamped
    per_round = (1.0 - survival ** (1.0 / rounds)) / 2.0
    derivative = (1.0 / rounds) * survival ** ((1.0 / rounds) - 1.0)
    return per_round, abs(derivative) * total_uncertainty


def _two_qubit_count(ops: dict[str, int]) -> int:
    names = {"cx", "cz", "swap", "ecr", "iswap", "rxx", "ryy", "rzz", "move"}
    return int(sum(count for name, count in ops.items() if name.lower() in names))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path | None) -> str:
    if path is None:
        return "missing"
    return str(path.relative_to(ROOT)).replace("\\", "/")


if __name__ == "__main__":
    main()
