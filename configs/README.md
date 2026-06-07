# Configs

Run one YAML config with:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Equivalent dry-run forms:

```bash
python main.py --dry-run --print-config configs/demo_stim_no_noise.yaml
python main.py --dry-run --print-config --config configs/demo_stim_no_noise.yaml
```

## Available Configs

| Config | Purpose |
| --- | --- |
| `demo_stim_no_noise.yaml` | Fast no-noise simulator smoke test. |
| `demo_stim_simple_noise.yaml` | Noisy simulator sanity check with observable-rate decoder. |
| `demo_stim_simple_noise_pymatching.yaml` | Noisy simulator baseline with PyMatching. |
| `sim_iqm_emerald_surface_d3_calibrated.yaml` | Rotated d3 simulator using Emerald per-qubit/per-coupler calibration noise. |
| `sim_iqm_emerald_surface_d3_unrotated_calibrated.yaml` | Unrotated d3 simulator using Emerald calibration noise. |
| `sim_iqm_emerald_surface_d5_calibrated.yaml` | Rotated d5 simulator using Emerald calibration noise and routed layout. |
| `baseline_surface_d3.yaml` | Simulator baseline template. |
| `iqm_surface_d3_baseline.yaml` | IQM hardware run with real Emerald patch selection. |
| `iqm_surface_d3_r1_native.yaml` | Short one-round d3 hardware sanity run on the corrected native Emerald patch. |
| `iqm_surface_d3_r1_no_initial_reset.yaml` | Same one-round native patch, but without explicit initial Qiskit reset gates. |
| `iqm_surface_d3_no_initial_reset.yaml` | D3 Emerald run without active resets, using virtualized repeated-measurement records. |
| `iqm_surface_d3_r2_no_active_reset.yaml` | Short no-active-reset D3 Emerald variant for reset A/B testing. |
| `iqm_surface_d5_baseline.yaml` | D5 IQM hardware run with real Emerald routed-layout selection. |
| `qpu_patch_calibration_example.yaml` | Full-chip calibration/topology input template for patch selection. |
| `2026-06-06T06_08_52.470451Z.json` | Real 54-qubit IQM observation dump, used as Emerald calibration input. |
| `2026-06-06T16_44_10.718568Z.json` | Real 20-qubit IQM observation dump, used as Garnet calibration input. |

Old planning-only configs are in `archive/configs/`.

## YAML Sections

### `experiment`

```yaml
experiment:
  name: iqm_surface_d3_baseline
  description: "Minimal surface-code memory experiment on IQM hardware."
  seed: 1
```

- `name`: output folder name under `results/`.
- `description`: human-readable note.
- `seed`: experiment-level note. The simulator seed currently comes from `backend.options.seed`.

### `code`

```yaml
code:
  family: surface_code
  distance: 3
  rounds: 1
  basis: both
  reset_mode: reset
```

- `family`: `surface_code`, `surface_code_iqm`, or `surface_code_unrotated`.
- `distance`: Stim generated surface-code distance.
- `rounds`: number of syndrome rounds.
- `basis`: `memory_z`, `memory_x`, or `both`.
- `reset_mode`: currently only `reset` behavior is implemented. `no_reset` is a future branch.

### `backend`

Simulator:

```yaml
backend:
  name: simulator
  shots: 1000
  options:
    seed: 1
```

IQM hardware:

```yaml
backend:
  name: iqm_hardware
  shots: 100
  options:
    server_url: https://resonance.meetiqm.com
    quantum_computer: garnet
    optimization_level: 3
    omit_initial_resets: false
    omit_repeated_resets: false
```

- `name`: `simulator` or `iqm_hardware`.
- `shots`: number of samples/jobs shots.
- `options.seed`: Stim sampler seed for simulator.
- `options.server_url`: IQM Resonance URL.
- `options.quantum_computer`: QPU name, for example `garnet`.
- `options.optimization_level`: Qiskit transpiler optimization level.
- `options.omit_initial_resets`: IQM A/B option. If `true`, leading Stim `R`/`RX` preparations are translated without explicit Qiskit reset gates; later syndrome-round resets are still kept.
- `options.omit_repeated_resets`: IQM A/B option. If `true`, repeated syndrome reset gates are omitted and raw records are XOR-converted into virtual reset-style measurements before Stim syndrome extraction.

For IQM auth, prefer:

```powershell
$env:IQM_TOKEN="your-token"
```

Do not also set `backend.options.token` when `IQM_TOKEN` exists in the environment.

### `noise`

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

Meaning:

- Simulator backend: these values create a noisy Stim circuit and affect samples.
- IQM backend: these values are not sent to the QPU. They define the Stim detector error model used by PyMatching.

Current implementation:

```text
one_qubit_error     -> after_clifford_depolarization
measurement_error   -> before_measure_flip_probability
reset_error         -> after_reset_flip_probability
idle_error          -> before_round_data_depolarization
two_qubit_error     -> present in YAML, not separately used yet
```

Calibration-aware simulator:

```yaml
noise:
  model: iqm_calibration
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
  options:
    apply_idle: true
    route_error_multiplier: 1.0
```

This uses the selected `mapping` to inject hardware-specific Stim noise:

```text
PRX error      -> DEPOLARIZE1 after 1Q gates
CZ error       -> DEPOLARIZE2 after 2Q gates
readout + QND  -> X/Z error before measurement
T2 idle error  -> DEPOLARIZE1 spread over TICKs
```

For QPU calibration:

- Full per-qubit/per-coupler data belongs in `mapping.calibration_file`.
- Scalar `noise.parameters` remains the simple detector-model approximation for PyMatching.
- Later, a richer error-model module should use the same calibration data to build better decoder weights.

### `decoder`

```yaml
decoder:
  name: pymatching
  options:
    noise_sweep_probabilities: [0.001, 0.003, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]
```

Available:

- `observable_rate`: sanity check only; counts observed logical flips directly.
- `pymatching`: real MWPM decoder from the Stim detector error model.
- `pymatching_calibrated`: MWPM decoder intended for `noise.model: iqm_calibration`.
- `pymatching.options.noise_sweep_probabilities`: optional diagnostic. It redecodes the same detector events with several uniform Stim noise probabilities and saves the sweep in `metrics.json`.

Placeholders:

- `gnn`
- `ising`

These are registered names, but they currently raise `NotImplementedError`.

### `mapping`

```yaml
mapping:
  strategy: none
  hardware_patch: null
```

Current behavior:

- `strategy: none` means Qiskit/IQM chooses layout and routing.
- `strategy: calibration_best_patch` selects an exact native hardware patch and passes `initial_layout` to Qiskit.
- `strategy: calibration_routed_layout` selects a low-cost initial layout when no exact native patch exists, then Qiskit routes missing edges.
- Real IQM observation dumps are supported directly. If they have no explicit coordinates, the selector uses the measured coupler graph.
- If no native graph patch exists, use `calibration_routed_layout` or `strategy: none`.
- IQM scoring uses PRX, readout, QND, idle/T2, and CZ calibration terms.
- `hardware_patch.stim_to_hardware` pins an exact Stim-qubit-to-QPU-qubit assignment and bypasses graph isomorphism tie-breaking.

Native d=3 patch selection:

```yaml
mapping:
  strategy: calibration_best_patch
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
  weights:
    one_qubit: 1.0
    two_qubit: 1.0
    measurement: 1.0
    reset: 1.0
    idle: 1.0
    qnd: 1.0
    max_coupler: 10.0
  options:
    exclude_qubits:
      - QB9
      - QB25
      - QB41
      - QB46
      - QB47
  hardware_patch:
    stim_to_hardware:
      "1": QB31
      "2": QB39
      "3": QB38
```

D5 routed layout:

```yaml
mapping:
  strategy: calibration_routed_layout
  calibration_file: configs/2026-06-06T06_08_52.470451Z.json
  weights:
    one_qubit: 1.0
    two_qubit: 1.0
    measurement: 1.0
    reset: 1.0
    idle: 1.0
    qnd: 1.0
    max_coupler: 10.0
    route_distance: 0.2
  options:
    seed: 1
    max_iterations: 5000
    exclude_qubits:
      - QB9
      - QB25
      - QB41
      - QB46
      - QB47
```

### `artifacts`

```yaml
artifacts:
  root: results
  save_raw_measurements: true
  save_syndromes: true
  save_report: true
```

Current behavior:

- `root` controls the output root.
- The save flags are descriptive for now. The current reporter writes the standard artifact set.
- New runs include `measurement_diagnostics.json`, which compares each raw measurement bit to ideal Stim one-rates and labels the mapped hardware qubit when available.

## Recommended QPU Config Pattern

Make one config per QPU:

```text
configs/iqm_garnet_surface_d3_baseline.yaml
configs/iqm_emerald_surface_d3_baseline.yaml
```

Change:

```yaml
backend:
  options:
    quantum_computer: garnet

mapping:
  strategy: calibration_best_patch
  calibration_file: configs/2026-06-06T16_44_10.718568Z.json
```

For d=5 on the current Emerald dump, native patch selection fails because the required surface-code interaction graph is not present. Use `calibration_routed_layout` for the d=5 baseline config.

## QPU Patch Calibration

The selector accepts either:

- the small documented template `qpu_patch_calibration_example.yaml`,
- the real IQM observation-set JSON files in this directory.

For template files, it uses:

- qubit `row` / `col` coordinates,
- Qiskit hardware `index`,
- per-qubit errors,
- native couplers and their two-qubit errors.

For IQM observation dumps, it extracts:

- one-qubit PRX error from PRX fidelity records, with Clifford fidelity as fallback,
- measurement error from SSRO records,
- QND failure from QND records,
- idle error from T2 echo or T2 records, assuming a 1 us round for scoring,
- CZ error from IRB CZ fidelity when present, otherwise RB CZ fidelity,
- native couplers from two-qubit records.

Reset errors are currently left at `0.0` in mapping scores; direct reset calibration should be added when available.

`calibration_best_patch` chooses the lowest-score native region for the generated surface-code interaction graph.

`calibration_routed_layout` chooses a low-cost layout even when some code interactions need routing. Current offline d=5 Emerald check:

```text
49 circuit qubits mapped
excluded bad qubits: QB9, QB25, QB41, QB46, QB47
50 / 80 unique code interactions are native
30 / 80 require routing
max hardware graph route distance: 5
```
