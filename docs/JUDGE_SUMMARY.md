# Judge Summary

## Goal

Build a modular QEC pipeline for the IQM challenge and minimize logical error rate (LER) on real hardware.

Fast judge entry points:

```text
judge_results/FINAL_ONE_PAGER.md
judge_results/README.md
judge_results/JUDGING_MATRIX.md
judge_results/plots/ler_vs_rounds_combined.png
judge_results/tables/swap_depth_summary.csv
```

## What We Built

```text
YAML config
-> Stim surface-code circuit
-> calibrated simulator or IQM hardware
-> detector events
-> decoder
-> LER, artifacts, and LER-vs-rounds plots
```

Main features:

- Stim source-of-truth circuits and detector models.
- Qiskit/IQM hardware execution path.
- IQM batch submission for hardware sweeps.
- Calibration-based Emerald/Garnet patch selection from real QPU observation dumps.
- Per-qubit/per-coupler calibrated Stim noise model.
- PyMatching decoders plus an experimental `pymatching_auto` route.
- Final-hour repetition-code module distilled from teammate code.
- Raw artifacts for every run: circuits, counts, measurements, syndromes, diagnostics, and metrics.

Repetition-code explanation: `docs/REPETITION_CODE_EXPLANATION.md`.

## What We Tried

- Distance-3 and distance-5 rotated surface-code memory experiments.
- Memory-Z and memory-X bases.
- Emerald and Garnet hardware inputs.
- Explicit reset, omitted initial reset, and no-active-reset variants.
- Native d=3 patch selection and routed d=5 layout selection.
- Calibrated simulator sweeps using real Emerald calibration data.
- Decoder weight sweeps and auto-selection.
- Low-syndrome postselection as a fast decoder-side improvement experiment.
- Repetition code on a fixed low-depth Garnet layout.

## Current Results

Latest normal simulator sweep, 2000 shots:

```text
config: configs/sweep_d3_best_sim.yaml
artifact: results/sweep_d3_best_sim_rounds_sweep/20260607T011525Z
rounds 1: memory_z 0.021,  memory_x 0.0265
rounds 3: memory_z 0.1675, memory_x 0.2025
rounds 5: memory_z 0.367,  memory_x 0.358
rounds 7: memory_z 0.468,  memory_x 0.4715
```

Latest matching IQM hardware sweep, 2000 shots:

```text
config: configs/sweep_d3_best_iqm.yaml
artifact: results/sweep_d3_best_iqm_rounds_sweep/20260607T011549Z
rounds 1: memory_z 0.049, memory_x 0.0545
rounds 3: memory_z 0.487, memory_x 0.4925
rounds 5: memory_z 0.484, memory_x 0.4965
rounds 7: memory_z 0.472, memory_x 0.4825
```

Latest postselected simulator sweep, keeping about half of shots:

```text
config: configs/sweep_d3_postselected_sim.yaml
artifact: results/sweep_d3_postselected_sim_rounds_sweep/20260607T012558Z
rounds 1: memory_z 0.0,    memory_x 0.0
rounds 3: memory_z 0.0929, memory_x 0.1028
rounds 5: memory_z 0.3135, memory_x 0.3211
rounds 7: memory_z 0.4538, memory_x 0.4650
```

Final repetition-code Garnet hardware sweep:

```text
artifact: results/final_rep_code_iqm_rounds_sweep/20260607T062249Z
code: d=3 repetition code, 5 Garnet qubits, 20000 shots
rounds 1:  total LER 0.00255 +/- 0.00036
rounds 9:  total LER 0.02245 +/- 0.00105
rounds 17: total LER 0.02800 +/- 0.00117
rounds 26: total LER 0.03325 +/- 0.00127
rounds 34: total LER 0.02450 +/- 0.00109
rounds 42: total LER 0.01460 +/- 0.00085
rounds 50: total LER 0.01630 +/- 0.00090
rounds 50 per-round LER: 0.000331 +/- 0.000018
```

Final fitted simulator sweep:

```text
artifact: results/final_rep_code_sim_rounds_sweep/20260607T062152Z
rounds 1:  total LER 0.00955 +/- 0.00069
rounds 9:  total LER 0.01285 +/- 0.00080
rounds 17: total LER 0.01435 +/- 0.00084
rounds 26: total LER 0.01675 +/- 0.00091
rounds 34: total LER 0.02230 +/- 0.00104
rounds 42: total LER 0.03325 +/- 0.00127
rounds 50: total LER 0.04340 +/- 0.00144
```

SWAP/depth evidence:

```text
artifact: judge_results/tables/swap_depth_summary.csv
literal transpiled swap gates: 0 in curated hardware sweeps
repetition code r=50: 200 logical two-qubit gates -> 219 transpiled two-qubit gates
routing overhead: +19 two-qubit gates
```

Curated judge pack:

```text
judge_results/README.md
judge_results/plots/ler_vs_rounds_combined.png
judge_results/plots/rep_code_per_round_ler.png
judge_results/tables/*.csv
```

## Interpretation

The one-round surface-code hardware result is useful and close to the calibrated simulator. The failure is repeated-round saturation: from round 3 onward, surface-code hardware LER is essentially random while the simulator degrades more gradually.

This points to missing hardware effects in our current model: repeated reset/readout behavior, timing, leakage, crosstalk, and pulse-level compilation overhead.

The repetition-code route is a pragmatic final improvement: it is much shallower, uses only 5 qubits, and targets one protected error channel instead of full surface-code correction. It was added after identifying that multi-round surface-code execution saturates on current hardware.

The fresh repetition-code hardware curve is non-monotonic after round 26. We treat this as an experimental observation, not as a monotonic threshold claim. The likely causes are extra syndrome history helping the decoder, hardware drift or batch-order effects, and reset/readout transients.

## Final Demo Commands

Build the judge pack:

```bash
python scripts/build_judge_pack.py
```

Run the final repetition-code hardware config:

```bash
python main.py configs/final_rep_code_iqm.yaml
```
