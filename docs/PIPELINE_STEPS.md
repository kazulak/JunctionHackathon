# Pipeline Steps

Run:

```bash
python main.py --config configs/demo_stim_no_noise.yaml
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

## Data Flow

The pipeline sends one result object into the next function:

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
