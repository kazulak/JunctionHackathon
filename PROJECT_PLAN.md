# Project Plan

## Goal

Build a modular offline QEC pipeline that minimizes logical error rate (LER) on IQM hardware, starting with a simulator baseline.

## Current Demo

- Code: real Stim distance-3 rotated surface-code memory circuits.
- Basis: memory-Z and memory-X in the same run.
- Backend: Stim local sampler.
- Noise: none.
- Syndrome extraction: provided `extract_syndromes.py`.
- Decoder: observable flip rate only, not a real decoder.
- Output: circuit, raw measurement head, syndromes, LER = 0, short report.

## First Noisy Check

- Config: `configs/demo_stim_simple_noise.yaml`.
- Noise: Stim `simple_depolarizing` parameters from YAML.
- Purpose: confirm noisy samples produce nonzero syndromes/logical flips.
- Decoder: still `observable_rate`, so this is not final decoded LER yet.

## First Real Baseline

- Code: distance-3 rotated surface code with Stim.
- Backend: simulator first, IQM Emerald later.
- Decoder: PyMatching first.
- Noise: simple configurable model first; calibration-aware model next.
- Output: LER, uncertainty, circuit metrics, syndrome diagnostics, saved artifacts.

## Approaches To Try

- Surface code vs color code.
- PyMatching vs GNN decoder vs NVIDIA Ising route.
- Reset vs no-reset syndrome rounds.
- Automatic transpiler layout vs custom Emerald patch mapping.
- Simple noise model vs calibration-aware model.
- Single patch vs multiple hardware patches.

## Architecture

- `main.py`: CLI entry point.
- `configs/`: YAML experiment definitions.
- `qec_pipeline/`: modular pipeline package.
- `qec_pipeline/codes/`: surface code, color code, future code families.
- `qec_pipeline/conversion.py`: source-circuit to backend-circuit conversion.
- `qec_pipeline/syndromes.py`: raw measurements to detector events.
- `qec_pipeline/decoders/`: PyMatching, GNN, Ising, future decoders.
- `qec_pipeline/backends/`: simulator and IQM hardware runners.
- `qec_pipeline/noise/`: simple and calibration-based noise models.
- `qec_pipeline/mapping/`: hardware qubit placement.
- `qec_pipeline/analysis/`: LER metrics and reports.
- `results/`: generated experiment outputs, ignored by git.

## Run

Dry-run the Stim no-noise pipeline:

```bash
python main.py --dry-run --print-config
```

Run the Stim no-noise pipeline:

```bash
python main.py
```

Run the noisy simulator check:

```bash
python main.py configs/demo_stim_simple_noise.yaml
```

Or use:

```bash
./scripts/run_demo.sh
```

Run the first real baseline later:

```bash
python main.py --config configs/baseline_surface_d3.yaml
```
