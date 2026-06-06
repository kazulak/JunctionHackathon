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
| `baseline_surface_d3.yaml` | Simulator baseline template. |
| `iqm_surface_d3_baseline.yaml` | Minimal IQM hardware run. |
| `experiment_matrix.yaml` | Planning file only; not executed by `main.py`. |

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

- `family`: only `surface_code` is implemented.
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
```

- `name`: `simulator` or `iqm_hardware`.
- `shots`: number of samples/jobs shots.
- `options.seed`: Stim sampler seed for simulator.
- `options.server_url`: IQM Resonance URL.
- `options.quantum_computer`: QPU name, for example `garnet`.
- `options.optimization_level`: Qiskit transpiler optimization level.

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

For QPU calibration values:

- Put QPU-specific values here for now.
- Use separate YAML files for separate QPUs.
- Later, move richer per-qubit/per-coupler data into a dedicated calibration error-model module.

### `decoder`

```yaml
decoder:
  name: pymatching
  options: {}
```

Available:

- `observable_rate`: sanity check only; counts observed logical flips directly.
- `pymatching`: real MWPM decoder from the Stim detector error model.

Placeholders:

- `gnn`
- `ising`

These are not wired into `pipeline.py` yet.

### `mapping`

```yaml
mapping:
  strategy: none
  hardware_patch: null
```

Current behavior:

- `strategy: none` means Qiskit/IQM chooses layout and routing.
- Custom hardware patch mapping is not implemented yet.

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

noise:
  parameters:
    one_qubit_error: <from QPU page>
    measurement_error: <from QPU page>
    reset_error: <from QPU page>
    idle_error: <estimated or from calibration>
```

Keep `two_qubit_error` in the file for documentation, but remember it needs a code upgrade before it influences the detector model separately.
