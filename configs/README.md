# Configs

Run one config:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Dry-run without executing:

```bash
python main.py --dry-run --print-config configs/sweep_d3_best_sim.yaml
```

## Active Files

| Config | Purpose |
| --- | --- |
| `demo_stim_no_noise.yaml` | No-noise simulator smoke test. |
| `sweep_d3_best_sim.yaml` | Main d3 calibrated simulator sweep config. |
| `sweep_d3_postselected_sim.yaml` | D3 simulator with low-syndrome postselection. |
| `sweep_d3_best_combined_sim.yaml` | Best reported-LER simulator recipe: postselection plus full PyMatching candidate set. |
| `sweep_d3_best_combined_iqm.yaml` | Best reported-LER IQM recipe: Emerald patch, omitted initial resets, DD attempt, postselection, full decoder candidates. |
| `sweep_d3_low_syndrome_sim.yaml` | D3 simulator with aggressive 25% low-syndrome postselection. |
| `sweep_d3_gated_decoder_sim.yaml` | D3 simulator with full-dataset gated MWPM/no-correction decoder. |
| `sweep_d3_decoder_improvements_sim.yaml` | D3 simulator with full-dataset correlated MWPM, MWPM ensembles, and gated candidates. |
| `sweep_d3_decoder_holdout_sim.yaml` | Same decoder candidates as above, but selected on one shot split and reported on held-out shots. |
| `sweep_d3_decoder_kfold_sim.yaml` | Same decoder candidates as above, evaluated with k-fold out-of-fold candidate selection. |
| `sim_iqm_emerald_surface_d3_calibrated.yaml` | Single d3 calibrated simulator run. |
| `sim_iqm_emerald_surface_d3_unrotated_calibrated.yaml` | Unrotated d3 simulator variant. |
| `sim_iqm_emerald_surface_d5_calibrated.yaml` | D5 calibrated simulator with routed layout. |
| `sweep_d3_best_iqm.yaml` | Hardware template matching the main d3 simulator route. Use only after simulator results justify it. |
| `2026-06-06T06_08_52.470451Z.json` | Emerald-like IQM calibration dump. |
| `2026-06-06T16_44_10.718568Z.json` | Garnet-like IQM calibration dump. |

## YAML Sections

### `experiment`

```yaml
experiment:
  name: sweep_d3_best_sim
  description: "D3 calibrated simulator sweep."
  seed: 1
```

- `name`: output folder under `results/`.
- `description`: free text.
- `seed`: experiment-level note; backend seed controls simulator sampling.

### `code`

```yaml
code:
  family: surface_code
  distance: 3
  rounds: 1
  basis: both
  reset_mode: reset
```

- `family`: `surface_code`, `surface_code_iqm`, `surface_code_unrotated`, or placeholder `color_code`.
- `distance`: code distance.
- `rounds`: syndrome rounds.
- `basis`: `memory_z`, `memory_x`, or `both`.
- `reset_mode`: currently only reset-style behavior is implemented.

### `backend`

Simulator:

```yaml
backend:
  name: simulator
  shots: 2000
  options:
    seed: 1
```

Hardware:

```yaml
backend:
  name: iqm_hardware
  shots: 2000
  options:
    server_url: https://resonance.meetiqm.com
    quantum_computer: emerald
    optimization_level: 3
    batch_submit: true
```

Notes:

- `backend.name`: `simulator` or `iqm_hardware`.
- `shots`: number of samples.
- `batch_submit: true`: sweeps submit all IQM jobs first, then wait.
- `omit_initial_resets: true`: skips the initial hardware reset when converting to Qiskit; this was the best hardware-side reset choice in hackathon runs.
- `dynamical_decoupling: true`: attempts Qiskit's XX DD pass after transpilation and records whether it applied.
- IQM token is read from `.env` or `IQM_TOKEN`.

### `noise`

Simple scalar noise:

```yaml
noise:
  model: simple_depolarizing
  parameters:
    one_qubit_error: 0.003
    two_qubit_error: 0.003
    measurement_error: 0.003
    reset_error: 0.003
    idle_error: 0.003
```

Calibration-aware noise:

```yaml
noise:
  model: iqm_calibration
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
  options:
    apply_idle: true
    route_error_multiplier: 1.0
    qnd_scale: 0.0
    idle_scale: 0.5
```

Meaning:

- Simulator: noise is injected into the Stim circuit and affects samples.
- IQM hardware: real hardware supplies the noise; YAML noise is still used to build the detector error model for decoding.
- `iqm_calibration` uses selected qubits/couplers from `mapping`.

### `decoder`

```yaml
decoder:
  name: pymatching_auto
  options:
    uniform_probabilities: [0.001, 0.003, 0.01, 0.02, 0.05]
```

Available:

- `observable_rate`: sanity check, no correction.
- `pymatching`: MWPM from the configured detector model.
- `pymatching_calibrated`: calibrated MWPM route.
- `pymatching_auto`: tries configured/calibrated and optional uniform detector models.
- `gnn`, `ising`: placeholders.

Postselection:

```yaml
decoder:
  name: pymatching_auto
  options:
    postselect_weight_quantile: 0.5
```

This reports LER only on kept low-syndrome shots.

Full-shot decoder experiments:

```yaml
decoder:
  name: pymatching_auto
  options:
    include_correlated_matching: true
    include_matching_ensembles: true
    gated_no_correction_quantiles: [0.25, 0.5, 0.75]
```

These keep all shots and add extra MWPM candidates. The selected candidate is written to `metrics.json`.

Held-out candidate selection:

```yaml
decoder:
  name: pymatching_auto
  options:
    candidate_selection_mode: holdout
    selection_fraction: 0.5
    selection_seed: 1
```

This selects the decoder candidate on `selection_fraction` of postselected shots and reports LER on the rest.

K-fold candidate selection:

```yaml
decoder:
  name: pymatching_auto
  options:
    candidate_selection_mode: kfold
    candidate_selection_folds: 5
    selection_seed: 1
```

This selects candidates on `k-1` folds and reports on the held-out fold, repeated until all shots are evaluated out-of-fold.

### `mapping`

No fixed layout:

```yaml
mapping:
  strategy: none
```

Calibration-selected native d3 patch:

```yaml
mapping:
  strategy: calibration_best_patch
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
  weights:
    one_qubit: 1.0
    two_qubit: 1.0
    measurement: 1.0
    idle: 1.0
    qnd: 1.0
    max_coupler: 10.0
  options:
    exclude_qubits: [QB9, QB25, QB41, QB46, QB47]
```

D5 currently needs routed layout selection:

```yaml
mapping:
  strategy: calibration_routed_layout
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
  weights:
    route_distance: 0.2
  options:
    seed: 1
    max_iterations: 5000
```

### `artifacts`

```yaml
artifacts:
  root: results
  save_raw_measurements: true
  save_syndromes: true
  save_report: true
```

Standard outputs are written under:

```text
results/<experiment>/<timestamp>/
```

For sweeps:

```text
results/<experiment>_rounds_sweep/<timestamp>/
```

When enabled, full arrays are also saved:

```text
raw_measurements.npz
syndromes.npz
```
