# Pipeline Steps

Run:

```bash
python main.py --config configs/demo_stim_no_noise.yaml
```

Run the first noisy simulator check:

```bash
python main.py configs/demo_stim_simple_noise.yaml
```

Run the first decoded simulator baseline:

```bash
python main.py configs/demo_stim_simple_noise_pymatching.yaml
```

Dry-run the minimal IQM baseline:

```bash
python main.py --dry-run --print-config configs/iqm_surface_d3_baseline.yaml
```

Equivalent forms:

```bash
python main.py configs/demo_stim_no_noise.yaml
python main.py --dry-run --print-config configs/demo_stim_no_noise.yaml
python main.py --dry-run --print-config --config configs/demo_stim_no_noise.yaml
```

## What Happens

1. Config loads from `configs/demo_stim_no_noise.yaml`.
2. `qec_pipeline/codes/surface_code.py` builds real Stim rotated surface-code memory circuits.
3. `qec_pipeline/backends/simulator.py` samples raw measurements with `stim.Circuit.compile_sampler`.
4. `qec_pipeline/syndromes.py` calls the provided `extract_syndromes.py`.
5. `qec_pipeline/decoders/observable_decoder.py` computes LER from observable flips.
6. `qec_pipeline/analysis/reports.py` writes inspectable artifacts.

## Simple Config Choices

Use YAML files in `configs/` to choose the experiment. For now these choices
work:

```yaml
code:
  basis: memory_z   # only Z
  basis: memory_x   # only X
  basis: both       # Z and X in one run

noise:
  model: no_noise
```

or:

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

The simulator is always Stim for these configs:

```yaml
backend:
  name: simulator
```

Available first-pass decoders:

```yaml
decoder:
  name: observable_rate
```

This counts observed logical flips directly. PyMatching and GNN come next.

```yaml
decoder:
  name: pymatching
```

This builds an MWPM decoder from the Stim detector error model.

## Data Flow

The pipeline sends one tuple into the next function:

```text
config
  -> (stim_circuit, detector_model, measurement_order, circuit_info)
  -> (measurements, counts, raw_info)
  -> (detection_events, observable_flips, syndrome_info)
  -> (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
  -> report files
```

For `basis: both`, the same flow runs once for `memory_z` and once for
`memory_x`. Artifacts are split into `memory_z/` and `memory_x/`.

## Expected No-Noise Result

- Raw measurements: may contain 0s and 1s from valid measurement randomness.
- Detection events: all zeros.
- Observable flips: all zeros.
- Logical failures: `0`.
- LER: `0.0`.
- Uncertainty: `0.0`.

For the current `distance=3`, `rounds=1`, `shots=32`, `basis=both` config,
expect these files under both `memory_z/` and `memory_x/`:

- `raw_measurements`: shape `(32, 17)`.
- `detection_events`: shape `(32, 8)`.
- `observable_flips`: shape `(32, 1)`.
- `num_qubits`: `26` Stim qubit indices, with 17 active measured code qubits.

## Output Files

Each run writes to `results/<experiment>/<timestamp>/`.

- `summary.md`: short human-readable combined result.
- `memory_z/`: memory-Z artifacts.
- `memory_x/`: memory-X artifacts.

Each basis folder contains:

- `circuit.stim`: generated Stim circuit.
- `circuit_metadata.json`: qubits, measurements, detectors, observables.
- `raw_measurements_head.csv`: first raw measurement rows.
- `raw_metadata.json`: simulator name and raw array shape.
- `detection_events_head.csv`: first syndrome rows.
- `observable_flips_head.csv`: first logical observable rows.
- `syndrome_metadata.json`: detector counts and syndrome statistics.
- `metrics.json`: LER, uncertainty, failures, shots.

## Visual Checks

After a run, plot the saved Stim circuit:

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
```

This writes `stim_timeline-svg.svg` inside each basis folder.

Convert the same saved Stim circuit to Qiskit and write a text drawing:

```bash
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp>
```

This writes:

- `qiskit_translation.txt`
- `qiskit_translation_metadata.txt`

Try a PNG Qiskit drawing:

```bash
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp> --png
```

The Qiskit converter used by this script is our small converter in
`qec_pipeline/conversion.py`. It exists because the provided converter does not
cover Stim memory-X instructions such as `RX` and `MX`.

## Where GNN Fits

GNN input should start from:

- `detection_events`: shape `(shots, num_detectors)`.
- Optional graph features from `circuit.detector_model`.
- Labels from `observable_flips` or final logical failures.

GNN output should match the decoder interface:

- `predicted_observables`: shape `(shots, num_observables)`.
- `logical_failures`.
- `ler`.
- `uncertainty`.

The first GNN task should be supervised learning on simulated noisy runs:

1. Generate noisy Stim samples.
2. Save `detection_events` as features.
3. Save `observable_flips` as labels.
4. Train the GNN to predict observable flips.
5. Compare its LER against PyMatching on the same samples.
