from __future__ import annotations

import argparse
import sys
from pathlib import Path

import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert saved Stim circuits to Qiskit and write visual checks."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Result directory, basis directory, or direct circuit.stim path.",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also try to save a matplotlib PNG drawing.",
    )
    args = parser.parse_args()

    circuit_paths = find_stim_circuits(args.path)
    if not circuit_paths:
        raise SystemExit(f"No circuit.stim files found under {args.path}")

    # OUR VISUAL CHECK SCRIPT.
    # Uses our minimal converter because it supports both memory-Z and memory-X.
    from qec_pipeline.conversion import stim_to_qiskit_minimal

    for circuit_path in circuit_paths:
        stim_circuit = stim.Circuit(circuit_path.read_text(encoding="utf-8"))
        qiskit_circuit, stim_to_dense, meas_order = stim_to_qiskit_minimal(stim_circuit)

        text_path = circuit_path.with_name("qiskit_translation.txt")
        text_path.write_text(str(qiskit_circuit), encoding="utf-8")

        meta_path = circuit_path.with_name("qiskit_translation_metadata.txt")
        meta_path.write_text(
            "\n".join(
                [
                    f"qiskit_qubits: {qiskit_circuit.num_qubits}",
                    f"qiskit_clbits: {qiskit_circuit.num_clbits}",
                    f"qiskit_depth: {qiskit_circuit.depth()}",
                    f"ops: {dict(qiskit_circuit.count_ops())}",
                    f"stim_to_dense: {stim_to_dense}",
                    f"meas_order: {meas_order}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        print(text_path)
        print(meta_path)

        if args.png:
            png_path = circuit_path.with_name("qiskit_translation.png")
            try:
                qiskit_circuit.draw(output="mpl", filename=str(png_path), fold=-1)
                print(png_path)
            except Exception as exc:
                print(f"Could not write PNG for {circuit_path}: {exc}")

    return 0


def find_stim_circuits(path: Path) -> list[Path]:
    if path.is_file() and path.name == "circuit.stim":
        return [path]
    if path.is_dir() and (path / "circuit.stim").exists():
        return [path / "circuit.stim"]
    if path.is_dir():
        basis_circuits = sorted(path.glob("*/circuit.stim"))
        if basis_circuits:
            return basis_circuits
        child_dirs = sorted([child for child in path.iterdir() if child.is_dir()])
        if child_dirs:
            return sorted(child_dirs[-1].glob("*/circuit.stim"))
    return []


if __name__ == "__main__":
    raise SystemExit(main())
