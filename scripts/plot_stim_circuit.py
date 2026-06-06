from __future__ import annotations

import argparse
from pathlib import Path

import stim


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot saved Stim circuits from results.")
    parser.add_argument(
        "path",
        type=Path,
        help="Result directory, basis directory, or direct circuit.stim path.",
    )
    parser.add_argument(
        "--diagram-type",
        default="timeline-svg",
        help="Stim diagram type, for example timeline-svg or matchgraph-svg.",
    )
    args = parser.parse_args()

    circuit_paths = find_stim_circuits(args.path)
    if not circuit_paths:
        raise SystemExit(f"No circuit.stim files found under {args.path}")

    for circuit_path in circuit_paths:
        circuit = stim.Circuit(circuit_path.read_text(encoding="utf-8"))
        output_path = circuit_path.with_name(f"stim_{args.diagram_type}.svg")
        output_path.write_text(str(circuit.diagram(args.diagram_type)), encoding="utf-8")
        print(output_path)

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
