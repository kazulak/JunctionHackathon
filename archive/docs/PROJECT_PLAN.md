# Project Plan

## Objective

Minimize logical error rate (LER) for an offline QEC memory experiment on IQM hardware.

The current working baseline is:

```text
Stim rotated surface code
-> IQM or Stim simulator
-> Stim syndrome extraction
-> PyMatching
-> LER
```

## What Works Now

- `main.py` runs YAML-configured experiments.
- `basis: both` runs `memory_z` and `memory_x` sequentially.
- Stim simulator works.
- Noisy Stim simulator works.
- PyMatching decoder works.
- IQM hardware backend works for minimal baseline runs.
- Results are saved under `results/<experiment>/<timestamp>/`.
- Circuit visualization scripts exist for Stim and Qiskit.
- Rounds sweeps produce CSV/JSON/PNG plots.
- Per-run diagnostics flag saturation, high detector firing, and transpilation depth blowups.
- Full-chip QPU calibration/topology data can select the best hardware patch through `mapping.strategy: calibration_best_patch`.
- D5 can use `mapping.strategy: calibration_routed_layout` to choose a 49-qubit initial layout when no native d=5 patch exists.

## Recorded Hardware Baseline

Latest useful baseline:

```text
Date: 2026-06-06
Run: results/iqm_surface_d3_baseline/20260606T163211Z
Code: distance 5, rounds 5, memory_z
Backend: IQM Emerald
Shots: 1000
Decoder: PyMatching
LER: 0.504 +/- 0.0158
Mean detector firing rate: 0.488
Saturated detectors: 115 / 120
Qiskit depth: 41
Transpiled depth: 276
Two-qubit gates after transpilation: 842
```

Interpretation: this is saturated logical output, not useful error correction yet. The strongest current evidence points to circuit depth/routing and hardware noise. Alternative bit-order decoding did not improve the saved d=5 run.

Latest mapped d=3 run:

```text
Date: 2026-06-06
Run: results/iqm_surface_d3_r1_native/20260606T193823Z
Code: distance 3, rounds 1, memory_z + memory_x
Backend: IQM Emerald
Shots: 1000
memory_z LER: 0.398 +/- 0.0155
memory_x LER: 0.435 +/- 0.0157
```

Interpretation: even one syndrome round is too noisy. Saved measurement data shows deterministic ancilla measurements firing around `0.36-0.48` on several mapped qubits. The converter now skips final unused ancilla resets and writes `measurement_diagnostics.json` to make this visible per measurement bit.

## Current Baseline Commands

Dry-run config and stages:

```bash
python main.py --dry-run --print-config configs/demo_stim_no_noise.yaml
```

No-noise simulator smoke test:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Noisy simulator with PyMatching:

```bash
python main.py configs/demo_stim_simple_noise_pymatching.yaml
```

Minimal IQM hardware baseline:

```bash
python main.py configs/iqm_surface_d3_baseline.yaml
```

Shortest native d=3 sanity check:

```bash
python main.py configs/iqm_surface_d3_r1_native.yaml
```

Plot a completed run:

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp> --png
```

## Best Next Steps

1. Run d=5 with the routed Emerald layout:

```yaml
mapping:
  strategy: calibration_routed_layout
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
```

Current offline d=5 layout check:

```text
excluded bad qubits: QB9, QB25, QB41, QB46, QB47
50 / 80 unique code interactions are native
30 / 80 require routing
max hardware graph route distance: 5
```

2. Rerun the fixed d=3 native patch first with `configs/iqm_surface_d3_r1_native.yaml`. The current code skips terminal unused ancilla resets, so compare the new one-round result against `results/iqm_surface_d3_r1_native/20260606T193823Z`.

3. Compare the new d=5 run against the saturated baseline:
   - LER,
   - detector firing rates,
   - transpiled depth,
   - two-qubit gate count.

4. Add a calibration-aware decoder/noise model:
   - input: IQM calibration table and circuit/mapping metadata
   - output: better decoder weights or better detector error model

5. Add mapping diagnostics:
   - final layout
   - two-qubit gate count
   - SWAP count
   - depth before and after transpilation

6. Replace the generic patch selector with an IQM/Emerald-specific selector if mentor data exposes better topology details.

7. Generate calibrated simulator data for GNN training.

8. Integrate colleague work only through stable boundaries:
   - code builder
   - backend
   - syndrome extraction
   - decoder
   - noise/error model
   - analysis/reporting

## Integration Slots

| Work | File |
| --- | --- |
| GNN decoder | `qec_pipeline/decoders/gnn_decoder.py` |
| NVIDIA Ising decoder | `qec_pipeline/decoders/ising_decoder.py` |
| Color code | `qec_pipeline/codes/color_code.py` |
| QPU patch selection | `qec_pipeline/mapping/patch_selection.py` |
| IQM calibration model | `qec_pipeline/noise/` |
| Custom hardware mapping | `qec_pipeline/mapping/` |
| Better reports/plots | `qec_pipeline/analysis/` or `scripts/` |

## Current Limitations

- `two_qubit_error` is listed in configs but not separately mapped into Stim noise yet.
- `reset_mode: no_reset` is not implemented.
- `experiment_matrix.yaml` is a planning file, not an executable matrix runner.
- GNN, Ising, and color code files are placeholders.
- Hardware mapping supports native d=3 patch selection and routed d=5 layout selection.
- The hardware backend does not inject artificial noise into the QPU.

## Questions For Organizers

- Which calibration numbers should be used for patch scoring and decoder weights?
- Can we programmatically access calibration data during the hackathon?
- Which QPU patches are recommended for a distance-3 rotated surface code?
- Does the judged result prefer lowest single-basis LER, average of X/Z, or both reported separately?
- Are mid-circuit measurement and reset expected to work well on the chosen QPU?
- Would a calibration-weighted PyMatching decoder be valued more than a GNN prototype?
- Are PulLA or dynamical-decoupling paths accessible with our account?

## Final Demo Story

Keep the final story simple:

1. We built a reproducible offline QEC pipeline.
2. We ran the same experiment on simulator and real IQM hardware.
3. We decoded detector events with PyMatching.
4. We compared QPUs or noise assumptions.
5. We identified the next physical bottleneck from syndrome and transpilation diagnostics.
