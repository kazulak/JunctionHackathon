from __future__ import annotations

import argparse
import sys
from pathlib import Path

import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.artifacts import find_stim_circuits


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


if __name__ == "__main__":
    raise SystemExit(main())
