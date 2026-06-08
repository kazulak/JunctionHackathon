# Pipeline Steps

## Commands

```bash
python main.py configs/demo_stim_no_noise.yaml
python scripts/sweep_rounds.py configs/sweep_d3_best_sim.yaml --rounds 1 7 4
python main.py --dry-run --print-config configs/sweep_d3_best_iqm.yaml
```

## Data Flow

```text
config YAML
-> basis expansion: memory_z / memory_x / both
-> code builder creates Stim circuit and detector model
-> backend returns raw measurements
-> Stim m2d converter creates detector events and observable flips
-> decoder predicts observables
-> predicted XOR observed observable gives logical failures
-> reports write metrics and artifacts
```

## Key Files

```text
qec_pipeline/config.py                 YAML loading
qec_pipeline/pipeline.py               orchestration
qec_pipeline/codes/                    Stim circuit builders
qec_pipeline/backends/simulator.py     local Stim sampling
qec_pipeline/backends/iqm_hardware.py  IQM execution
qec_pipeline/syndrome_extraction.py    measurements -> detector events
qec_pipeline/decoders/                 decoders
qec_pipeline/analysis/reports.py       artifacts
qec_pipeline/sweeps.py                 rounds sweeps
```

## Artifact Layout

Single run:

```text
results/<experiment>/<timestamp>/
```

Sweep:

```text
results/<experiment>_rounds_sweep/<timestamp>/
```

Per basis:

```text
circuit.stim
circuit_metadata.json
raw_metadata.json
syndrome_metadata.json
metrics.json
diagnostics.json
measurement_diagnostics.json
raw_measurements_head.csv
detection_events_head.csv
observable_flips_head.csv
counts.json                 # hardware only
qiskit_circuit.txt          # hardware only
transpiled_circuit.txt      # hardware only
```

## Expected Smoke Test

For `configs/demo_stim_no_noise.yaml`:

- detector events should be all zero,
- observable flips should be all zero,
- logical failures should be zero,
- LER should be `0.0`.

## Visual Checks

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp>
```

## Debug Order

When LER is strange, inspect:

1. `circuit_metadata.json`
2. `raw_metadata.json`
3. `raw_measurements_head.csv`
4. `detection_events_head.csv`
5. `syndrome_metadata.json`
6. `metrics.json`
7. `transpiled_circuit.txt` for hardware runs

LER near `0.5` means the logical output is basically random. Check detector firing rates and transpiled depth before assuming the decoder is the only issue.
