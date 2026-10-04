"""Rank native surface-code patches on a calibration file and print the best one as YAML.

    python scripts/select_patch.py configs/hw_d3_noreset_dd_iqm.yaml \\
        --calibration configs/calibration/emerald_<timestamp>Z.json --top 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.codes import get_code_builder
from qec_pipeline.config import load_experiment_config
from qec_pipeline.mapping import active_stim_to_dense, rank_calibration_best_patches
from qec_pipeline.mapping.patch_selection import select_fixed_stim_to_hardware_patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path, help="Config whose code and mapping weights are used.")
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    code = dict(config["code"], rounds=max(2, int(config["code"].get("rounds", 1))))
    stim_circuit = get_code_builder(code.get("family", "surface_code"))(
        code, {"model": "no_noise", "parameters": {}}, "memory_z"
    )[0]
    stim_to_dense = active_stim_to_dense(stim_circuit)
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    weights = config["mapping"].get("weights")
    options = config["mapping"].get("options") or {}

    ranked = rank_calibration_best_patches(stim_circuit, stim_to_dense, calibration, weights=weights, options=options)
    print(f"{len(ranked)} native patches; lower score is better")
    for candidate in ranked[: args.top]:
        print(f"  {candidate['score']:.4f}  data {candidate['data_hardware']}  ancilla {candidate['ancilla_hardware']}")

    pinned = (config["mapping"].get("hardware_patch") or {}).get("stim_to_hardware")
    if pinned:
        current = select_fixed_stim_to_hardware_patch(
            stim_circuit, stim_to_dense, calibration, pinned, weights=weights, options=options
        )
        print(f"Currently pinned patch scores {current['score']:.4f}")

    print("\nPaste under mapping: to pin the best patch")
    print(yaml.safe_dump({"hardware_patch": {"stim_to_hardware": ranked[0]["stim_to_hardware"]}}, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
