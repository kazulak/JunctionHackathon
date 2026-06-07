# Judge Summary

## Goal

Build a modular QEC pipeline for the IQM challenge and minimize logical error rate (LER) on real hardware.

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
- Calibration-based Emerald patch selection from real QPU observation dumps.
- Per-qubit/per-coupler calibrated Stim noise model.
- PyMatching decoders plus an experimental `pymatching_auto` route.
- Raw artifacts for every run: circuits, counts, measurements, syndromes, diagnostics, and metrics.

## What We Tried

- Distance-3 and distance-5 rotated surface-code memory experiments.
- Memory-Z and memory-X bases.
- Emerald and Garnet hardware inputs.
- Explicit reset, omitted initial reset, and no-active-reset variants.
- Native d=3 patch selection and routed d=5 layout selection.
- Calibrated simulator sweeps using real Emerald calibration data.
- Decoder weight sweeps and auto-selection.
- Low-syndrome postselection as a fast decoder-side improvement experiment.

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

## Interpretation

The one-round hardware result is useful and close to the calibrated simulator. The failure is repeated-round saturation: from round 3 onward, hardware LER is essentially random while the simulator degrades more gradually.

This points to missing hardware effects in our current model: repeated reset/readout behavior, timing, leakage, crosstalk, and pulse-level compilation overhead.

## Next Run

Run the paired postselected hardware sweep:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_postselected_iqm.yaml --rounds 1 7 4
```

If it improves round 3 hardware LER, decoder-side filtering has value. If it does not, the next priority is PulLA/DD or a more realistic repeated-round hardware noise model.
