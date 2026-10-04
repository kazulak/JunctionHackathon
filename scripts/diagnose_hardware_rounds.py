"""Diagnose how a rounds sweep degrades, round by round (ERRATA E5).

For every run in a sweep and every basis this reports:

- ancilla P(1) per syndrome round, split into X-type and Z-type ancillas;
- detector firing rate per detector time layer;
- raw (uncorrected) logical-observable flip rate vs the decoded LER.

If the raw observable is already ~0.5, the data qubits were scrambled before
decoding and no decoder can help. Requires runs saved with
`artifacts.save_raw_measurements: true`.

    python scripts/diagnose_hardware_rounds.py results/<sweep>/<timestamp> --output <dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.measurements import measurement_order_from_stim_circuit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep_dir", type=Path, nargs="+", help="Sweep directories (results/<sweep>/<ts>).")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for sweep_dir in args.sweep_dir:
        for basis_dir in sorted(sweep_dir.glob("runs/*/*/memory_*")):
            rows.append(diagnose_run(basis_dir, sweep_dir))
    if not rows:
        raise SystemExit("No runs with raw_measurements.npz found.")

    args.output.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output / "round_diagnostics.csv", rows)
    (args.output / "round_diagnostics.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (args.output / "summary.md").write_text(_summary(rows), encoding="utf-8")
    print(f"Diagnostics: {args.output}")
    return 0


def diagnose_run(basis_dir: Path, sweep_dir: Path) -> dict[str, Any]:
    circuit = stim.Circuit.from_file(basis_dir / "circuit.stim")
    measurements = np.load(basis_dir / "raw_measurements.npz")["measurements"].astype(bool)
    metrics = json.loads((basis_dir / "metrics.json").read_text(encoding="utf-8"))
    raw_metadata = json.loads((basis_dir / "raw_metadata.json").read_text(encoding="utf-8"))

    detections, observables = circuit.compile_m2d_converter().convert(
        measurements=measurements,
        separate_observables=True,
    )
    return {
        "sweep": sweep_dir.as_posix(),
        "job_id": raw_metadata.get("job_id"),
        "basis": basis_dir.name,
        "rounds": int(metrics.get("rounds") or _rounds_from_path(basis_dir)),
        "shots": int(len(measurements)),
        "raw_observable_flip_rate": float(observables.any(axis=1).mean()),
        "decoded_ler": float(metrics["ler"]),
        "x_ancilla_one_rate_by_round": ancilla_one_rate_by_round(circuit, measurements, "X"),
        "z_ancilla_one_rate_by_round": ancilla_one_rate_by_round(circuit, measurements, "Z"),
        "detector_rate_by_layer": detector_rate_by_layer(circuit, detections),
    }


def ancilla_one_rate_by_round(circuit: stim.Circuit, measurements: np.ndarray, kind: str) -> list[float]:
    """P(measured 1) for each syndrome round, averaged over ancillas of one type.

    X-type ancillas are the reset-and-measured qubits that receive Hadamards in a
    standard Stim surface-code circuit; the rest are Z-type.
    """
    order = measurement_order_from_stim_circuit(circuit)
    flattened = list(circuit.flattened())
    hadamard_qubits = {target.value for item in flattened if item.name == "H" for target in item.targets_copy()}
    ancillas = {target.value for item in flattened if item.name == "MR" for target in item.targets_copy()}
    wanted = {qubit for qubit in ancillas if (qubit in hadamard_qubits) == (kind == "X")}

    by_round: dict[int, list[float]] = {}
    seen: dict[int, int] = {}
    for index, qubit in enumerate(order):
        if qubit not in ancillas:
            continue
        seen[qubit] = seen.get(qubit, 0) + 1
        if qubit in wanted:
            by_round.setdefault(seen[qubit], []).append(float(measurements[:, index].mean()))
    return [float(np.mean(by_round[key])) for key in sorted(by_round)]


def detector_rate_by_layer(circuit: stim.Circuit, detections: np.ndarray) -> list[float]:
    """Mean detector firing rate per time coordinate (one layer per round, plus the final layer)."""
    layers: dict[int, list[int]] = {}
    for detector, coordinates in circuit.get_detector_coordinates().items():
        layers.setdefault(int(coordinates[-1]), []).append(detector)
    return [float(detections[:, layers[key]].mean()) for key in sorted(layers)]


def _rounds_from_path(basis_dir: Path) -> int:
    name = basis_dir.parent.parent.name
    return int(name.rsplit("_", 1)[-1])


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            flat = {key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()}
            writer.writerow(flat)


def _summary(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Round-by-round hardware diagnostics",
        "",
        "Raw observable = logical observable from the final data measurement with no correction.",
        "If it is ~0.5, the data qubits were scrambled before decoding.",
        "",
        "| Sweep | Basis | Rounds | Shots | Raw observable flip | Decoded LER "
        "| X-ancilla P(1) by round | Z-ancilla P(1) by round | Detector rate by layer |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in sorted(rows, key=lambda item: (item["sweep"], item["basis"], item["rounds"])):
        lines.append(
            f"| {Path(row['sweep']).parent.name} | {row['basis']} | {row['rounds']} | {row['shots']} | "
            f"{row['raw_observable_flip_rate']:.3f} | {row['decoded_ler']:.3f} | "
            f"{_fmt(row['x_ancilla_one_rate_by_round'])} | {_fmt(row['z_ancilla_one_rate_by_round'])} | "
            f"{_fmt(row['detector_rate_by_layer'])} |"
        )
    return "\n".join(lines) + "\n"


def _fmt(values: list[float]) -> str:
    return " ".join(f"{value:.2f}" for value in values)


if __name__ == "__main__":
    raise SystemExit(main())
