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

Plot a completed run:

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp> --png
```

## Best Next Steps

1. Verify hardware artifacts:
   - `circuit.stim`
   - `qiskit_circuit.txt`
   - `transpiled_circuit.txt`
   - `counts.json`
   - `detection_events_head.csv`
   - `metrics.json`

2. Make one config per QPU:
   - `configs/iqm_garnet_surface_d3_baseline.yaml`
   - `configs/iqm_emerald_surface_d3_baseline.yaml`

3. Replace equal noise values with QPU calibration-derived values:
   - readout error -> `measurement_error`
   - reset error -> `reset_error`
   - one-qubit gate error -> `one_qubit_error`
   - idle/decoherence estimate -> `idle_error`
   - two-qubit gate error -> keep in YAML for now, then implement real use

4. Add a calibration-aware error model:
   - input: IQM calibration table and circuit/mapping metadata
   - output: better decoder weights or better detector error model

5. Add mapping diagnostics:
   - final layout
   - two-qubit gate count
   - SWAP count
   - depth before and after transpilation

6. Integrate colleague work only through stable boundaries:
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
| IQM calibration model | `qec_pipeline/noise/` |
| Custom hardware mapping | `qec_pipeline/mapping/` |
| Better reports/plots | `qec_pipeline/analysis/` or `scripts/` |

## Current Limitations

- `two_qubit_error` is listed in configs but not separately mapped into Stim noise yet.
- `reset_mode: no_reset` is not implemented.
- `experiment_matrix.yaml` is a planning file, not an executable matrix runner.
- GNN, Ising, and color code files are placeholders.
- Hardware mapping is automatic through Qiskit/IQM for now.
- The hardware backend does not inject artificial noise into the QPU.

## Questions For Organizers

- Which calibration numbers should be used for decoder weights: average, median, worst-case, or per-qubit/per-coupler?
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
