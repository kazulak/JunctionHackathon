from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.artifacts import utc_timestamp
from qec_pipeline.codes import get_code_builder
from qec_pipeline.config import load_experiment_config
from qec_pipeline.mapping import active_stim_to_dense, rank_calibration_best_patches
from qec_pipeline.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Error budget for the calibration-informed simulator: halve one noise source at a "
            "time and see how much LER moves. This is a sensitivity study, NOT a calibration; "
            "use scripts/fit_noise_to_hardware.py to fit scales to hardware."
        )
    )
    parser.add_argument("config", type=Path, help="Base calibrated simulator YAML.")
    parser.add_argument("--basis", default="memory_z", choices=["memory_z", "memory_x", "both"])
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument(
        "--top-patches",
        type=int,
        default=0,
        help="Also test this many top native calibration patches.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Optional output root. Defaults to artifacts.root from YAML.",
    )
    args = parser.parse_args()

    base_config = load_experiment_config(args.config)
    search_dir = _make_search_dir(base_config, args.output_root)
    run_root = search_dir / "runs"

    configs = _noise_variant_configs(base_config, args.basis, args.shots, run_root)
    if args.top_patches:
        configs.extend(
            _patch_variant_configs(
                base_config,
                args.basis,
                args.shots,
                run_root,
                args.top_patches,
            )
        )

    rows = []
    for config in configs:
        run_dir, basis_results, _notes = run_pipeline(config)
        for basis, _circuit, _raw, _syndromes, _decoded, metrics in basis_results:
            rows.append(
                {
                    "variant": config["_search_variant"],
                    "basis": basis,
                    "ler": float(metrics["ler"]),
                    "uncertainty": float(metrics["uncertainty"]),
                    "logical_failures": int(metrics["logical_failures"]),
                    "shots": int(metrics["shots"]),
                    "run_dir": str(run_dir),
                }
            )

    _write_outputs(search_dir, rows, configs)
    print(f"Error-budget artifacts: {search_dir}")
    for row in rows:
        print(f"{row['variant']:28s} {row['basis']}: LER {row['ler']:.4g} +/- {row['uncertainty']:.2g}")
    return 0


def _noise_variant_configs(
    base_config: dict[str, Any],
    basis: str,
    shots: int,
    run_root: Path,
) -> list[dict[str, Any]]:
    base_options = base_config["noise"].get("options", {}) or {}
    variants = [("baseline", {})]
    for option in ["two_qubit_scale", "measurement_scale", "idle_scale", "one_qubit_scale"]:
        halved = 0.5 * float(base_options.get(option, 1.0))
        variants.append((f"{option.removesuffix('_scale')}_halved", {option: halved}))
    return [
        _config_with_noise_options(base_config, basis, shots, run_root, name, options)
        for name, options in variants
    ]


def _patch_variant_configs(
    base_config: dict[str, Any],
    basis: str,
    shots: int,
    run_root: Path,
    top_patches: int,
) -> list[dict[str, Any]]:
    mapping = base_config["mapping"]
    if mapping.get("strategy") != "calibration_best_patch":
        return []

    code = copy.deepcopy(base_config["code"])
    code["basis"] = basis if basis != "both" else "memory_z"
    circuit = get_code_builder(code.get("family", "surface_code"))(
        code,
        base_config["noise"],
        code["basis"],
    )
    stim_circuit, _detector_model, _measurement_order, _circuit_info = circuit
    stim_to_dense = active_stim_to_dense(stim_circuit)
    calibration = yaml.safe_load(Path(mapping["calibration_file"]).read_text(encoding="utf-8")) or {}
    ranked = rank_calibration_best_patches(
        stim_circuit,
        stim_to_dense,
        calibration,
        weights=mapping.get("weights"),
        options=mapping.get("options"),
    )

    configs = []
    for index, patch in enumerate(ranked[:top_patches], start=1):
        config = _config_with_noise_options(
            base_config,
            basis,
            shots,
            run_root,
            f"patch_{index:02d}",
            {},
        )
        config["mapping"]["hardware_patch"] = {
            "stim_to_hardware": patch["stim_to_hardware"],
        }
        config["_patch_score"] = patch["score"]
        configs.append(config)
    return configs


def _config_with_noise_options(
    base_config: dict[str, Any],
    basis: str,
    shots: int,
    run_root: Path,
    variant: str,
    noise_options: dict[str, float],
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["experiment"]["name"] = f"{base_config['experiment']['name']}_{variant}"
    config["code"]["basis"] = basis
    config["backend"]["shots"] = shots
    config["artifacts"]["root"] = str(run_root)
    config.setdefault("noise", {}).setdefault("options", {})
    config["noise"]["options"].update(noise_options)
    config["_search_variant"] = variant
    return config


def _make_search_dir(base_config: dict[str, Any], output_root: Path | None) -> Path:
    timestamp = utc_timestamp()
    root = output_root or Path(base_config["artifacts"].get("root", "results"))
    search_dir = root / f"{base_config['experiment']['name']}_error_budget" / timestamp
    search_dir.mkdir(parents=True, exist_ok=False)
    return search_dir


def _write_outputs(
    search_dir: Path,
    rows: list[dict[str, Any]],
    configs: list[dict[str, Any]],
) -> None:
    fieldnames = [
        "variant",
        "basis",
        "ler",
        "uncertainty",
        "logical_failures",
        "shots",
        "run_dir",
    ]
    with (search_dir / "search_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "rows": rows,
        "variants": [
            {
                "variant": config["_search_variant"],
                "noise_options": config.get("noise", {}).get("options", {}),
                "patch_score": config.get("_patch_score"),
            }
            for config in configs
        ],
    }
    (search_dir / "search_results.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Simulator Error Budget",
        "",
        "Each variant halves one noise source. This is a sensitivity study, not a calibration.",
        "",
        "| Variant | Basis | LER | Uncertainty | Failures | Shots |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {row['basis']} | {row['ler']} | "
            f"{row['uncertainty']} | {row['logical_failures']} | {row['shots']} |"
        )
    (search_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
