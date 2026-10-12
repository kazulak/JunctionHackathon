# Pipeline

## Data flow

```text
config YAML
-> basis expansion: memory_z / memory_x / both
-> code builder: Stim circuit + detector error model (+ calibration noise)
-> backend: Stim simulator or IQM hardware -> raw measurements
-> Stim m2d converter: detector events + observable flips
-> decoder: predicted observables
-> predicted XOR observed = logical failures -> LER, Wilson interval, per-round fit
-> artifacts in results/
```

## Key files

```text
qec_pipeline/config.py                  YAML loading, validation, command-line overrides (--set)
qec_pipeline/pipeline.py                run_experiments: build -> execute -> decode -> artifacts (single runs and sweeps)
qec_pipeline/sweeps.py                  LER-vs-rounds sweeps, IQM preflight, re-decoding saved runs
qec_pipeline/circuit_preparation.py     code circuit + hardware mapping + calibration noise for one basis
qec_pipeline/codes/                     surface-code builders (rotated, unrotated, IQM), mid-circuit reset strategies
qec_pipeline/noise/iqm_calibration.py   calibration-informed Stim noise (docs/CALIBRATED_SIMULATION.md)
qec_pipeline/mapping/calibration.py     IQM calibration files -> per-qubit / per-coupler error table
qec_pipeline/mapping/patch_selection.py native patch ranking, pinned patches, routed layouts
qec_pipeline/conversion.py              Stim -> Qiskit (grouped readout, feed-forward)
qec_pipeline/backends/                  simulator and IQM runners
qec_pipeline/syndromes.py               measurements -> detector events
qec_pipeline/decoders/                  decoders; scoring.py turns predictions into logical failures
qec_pipeline/analysis/                  metrics and fits, run reports, sweep tables, plots
qec_pipeline/artifacts.py               result folders: writing and reading saved runs
qec_pipeline/stim_utils.py              small Stim circuit helpers shared by all stages
```

## Artifacts

A single run writes `results/<experiment>/<timestamp>/`; a sweep writes `results/<experiment>_rounds_sweep/<timestamp>/`
with `sweep_results.csv/json`, `summary.md`, a plot, and one run folder per round count. Per basis:

```text
circuit.stim, circuit_metadata.json       circuit and its parameters
raw_metadata.json                         backend info; on IQM: job ID, calibration set, physical qubits
syndrome_metadata.json, metrics.json      detector statistics and LER
diagnostics.json, measurement_diagnostics.json
*_head.csv                                first rows of measurements, detection events, observable flips
counts.json, qiskit_circuit.txt, transpiled_circuit_virtual_order.txt   hardware only
```

Debug order when an LER looks wrong: `circuit_metadata.json` → `raw_metadata.json` → `raw_measurements_head.csv` →
`detection_events_head.csv` → `syndrome_metadata.json` → `metrics.json`. An LER near 0.5 means the logical output is
random: check detector firing rates per round (`scripts/diagnose_hardware_rounds.py`) before blaming the decoder.

Visual checks:

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp>
```

## Extending

Each component is a function registered by name in its package `__init__.py` and selected from YAML.

| Component | Signature | Registry | YAML | Available |
| --- | --- | --- | --- | --- |
| Code | `build(code, noise, basis) -> (stim_circuit, detector_model, measurement_order, circuit_info)` | `qec_pipeline/codes/__init__.py` | `code.family` | `surface_code`, `surface_code_iqm`, `surface_code_unrotated` |
| Decoder | `decode(decoder, circuit, syndromes) -> (predicted, failures, ler, uncertainty, info)` | `qec_pipeline/decoders/__init__.py` | `decoder.name` | `observable_rate`, `pymatching`, `pymatching_calibrated`, `pymatching_auto`, `pymatching_pij` |
| Backend | `run(backend, circuit) -> (measurements, counts, raw_info)` | `qec_pipeline/backends/__init__.py` | `backend.name` | `simulator`, `iqm_hardware` |

Add a test in `tests/` for every new component.
