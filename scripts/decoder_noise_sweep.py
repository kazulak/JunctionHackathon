from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.decoders.pymatching_decoder import pymatching_noise_sweep
from qec_pipeline.measurements import counts_to_measurement_array, virtualize_omitted_repeated_resets
from qec_pipeline.syndrome_extraction import extract_syndromes


DEFAULT_PROBABILITIES = [0.001, 0.003, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Redecode saved hardware results with several PyMatching noise weights."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Result directory or one basis directory.",
    )
    parser.add_argument(
        "--probabilities",
        type=float,
        nargs="+",
        default=DEFAULT_PROBABILITIES,
        help="Uniform Stim noise probabilities to try.",
    )
    args = parser.parse_args()

    basis_dirs = find_basis_dirs(args.path)
    if not basis_dirs:
        raise SystemExit(f"No basis result directories found under {args.path}")

    for basis_dir in basis_dirs:
        rows = sweep_basis_dir(basis_dir, args.probabilities)
        output_path = basis_dir / "decoder_noise_sweep.json"
        output_path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        best = min(rows, key=lambda row: row["ler"])
        print(
            f"{basis_dir.name}: best LER {best['ler']} at p={best['probability']} "
            f"({best['logical_failures']}/{best['shots']})"
        )
        print(output_path)

    return 0


def find_basis_dirs(path: Path) -> list[Path]:
    if path.is_dir() and (path / "circuit.stim").exists():
        return [path]
    if path.is_dir():
        basis_dirs = [
            child
            for child in sorted(path.iterdir())
            if child.is_dir() and (child / "circuit.stim").exists()
        ]
        if basis_dirs:
            return basis_dirs
        child_dirs = [child for child in sorted(path.iterdir()) if child.is_dir()]
        if child_dirs:
            return find_basis_dirs(child_dirs[-1])
    return []


def sweep_basis_dir(basis_dir: Path, probabilities: list[float]) -> list[dict]:
    stim_circuit = stim.Circuit((basis_dir / "circuit.stim").read_text(encoding="utf-8"))
    raw_info = json.loads((basis_dir / "raw_metadata.json").read_text(encoding="utf-8"))
    counts = json.loads((basis_dir / "counts.json").read_text(encoding="utf-8"))

    measurements = counts_to_measurement_array(
        counts,
        num_measurements=stim_circuit.num_measurements,
        total_shots=int(raw_info["shots"]),
    )
    if raw_info.get("omit_repeated_resets"):
        measurements = virtualize_omitted_repeated_resets(
            measurements,
            raw_info["meas_order"],
        )

    syndromes = extract_syndromes(measurements, stim_circuit)
    return pymatching_noise_sweep(
        stim_circuit,
        syndromes["det_events"],
        syndromes["obs_flips"],
        probabilities,
    )


if __name__ == "__main__":
    raise SystemExit(main())
