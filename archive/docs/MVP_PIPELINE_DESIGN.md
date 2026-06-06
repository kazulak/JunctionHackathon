# MVP Pipeline Design

This document describes the current architecture, not an ideal future system. The implementation is intentionally simple: plain YAML config, plain Python dictionaries, and tuple outputs passed from one stage to the next.

## Goal

Get the logical error rate as low as possible for an offline QEC memory experiment on IQM hardware.

Current baseline:

- Distance-5 rotated surface code.
- `memory_z` first.
- Stim as circuit and detector source of truth.
- IQM hardware through Qiskit/IQM.
- PyMatching decoder.
- Saved artifacts so hardware data can be redecoded without rerunning QPU jobs.

Recorded hardware result:

```text
Run: results/iqm_surface_d3_baseline/20260606T163211Z
Code: d=5, rounds=5, memory_z
Shots: 1000
LER: 0.504 +/- 0.0158
Mean detector firing rate: 0.488
Saturated detectors: 115 / 120
Transpiled depth: 276 vs Qiskit depth 41
```

This is saturated behavior. It proves the pipeline runs on hardware, but the current automatic mapping/routing is not yet useful error correction.

Mapped d=3 hardware result:

```text
Run: results/iqm_surface_d3_baseline/20260606T180519Z
Code: d=3, rounds=5, memory_z + memory_x
Shots: 100
memory_z LER: 0.43 +/- 0.0495
memory_x LER: 0.46 +/- 0.0498
```

## Current Pipeline

The orchestrator is `qec_pipeline/pipeline.py`.

```text
config
  -> build_surface_code_circuit
  -> run_simulator_backend or run_iqm_hardware_backend
  -> extract_detection_events
  -> decode_observable_rate or decode_with_pymatching
  -> write_run_artifacts + write_run_summary
```

Concrete tuple flow:

```text
config
  -> (stim_circuit, detector_model, measurement_order, circuit_info)
  -> (measurements, counts, raw_info)
  -> (detection_events, observable_flips, syndrome_info)
  -> (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
```

For `code.basis: both`, the same flow runs twice:

```text
memory_z
memory_x
```

## Implemented Modules

| Area | File | Current status |
| --- | --- | --- |
| CLI | `main.py` | Works with positional config or `--config`; supports `--dry-run` and `--print-config`. |
| Config loading | `qec_pipeline/config.py` | Loads YAML into a normal dict. |
| Orchestration | `qec_pipeline/pipeline.py` | Simple stage-by-stage tuple flow. |
| Surface code | `qec_pipeline/codes/surface_code.py` | Builds Stim generated rotated memory circuits. |
| Simulator | `qec_pipeline/backends/simulator.py` | Uses Stim `compile_sampler`. |
| IQM hardware | `qec_pipeline/backends/iqm_hardware.py` | Converts to Qiskit, transpiles, runs on IQM, converts counts to measurement array. |
| Conversion | `qec_pipeline/conversion.py` | Minimal Stim-to-Qiskit converter including `RX`, `MX`, `MRX`. |
| Syndromes | `qec_pipeline/syndromes.py` | Calls `qec_pipeline/syndrome_extraction.py`. |
| Sanity decoder | `qec_pipeline/decoders/observable_decoder.py` | Counts observable flips directly; not a real decoder. |
| PyMatching | `qec_pipeline/decoders/pymatching_decoder.py` | Builds MWPM decoder from Stim detector error model. |
| Reports | `qec_pipeline/analysis/reports.py` | Writes circuit, metadata, measurement heads, syndrome heads, metrics, summary. |
| Plots | `scripts/plot_stim_circuit.py`, `scripts/plot_qiskit_translation.py` | Visual inspection helpers. |
| Sweeps | `scripts/sweep_rounds.py`, `qec_pipeline/sweeps.py` | Runs LER vs rounds sweeps and writes CSV/JSON/PNG. |
| Patch selection | `qec_pipeline/mapping/patch_selection.py` | Scores full-chip calibration/topology data and selects the best `initial_layout`. |

## Current Configs

| Config | Purpose |
| --- | --- |
| `configs/demo_stim_no_noise.yaml` | Fast no-noise pipeline smoke test. |
| `configs/demo_stim_simple_noise.yaml` | Noisy simulator sanity check using observable-rate decoder. |
| `configs/demo_stim_simple_noise_pymatching.yaml` | First real noisy simulator baseline with PyMatching. |
| `configs/baseline_surface_d3.yaml` | Simulator baseline template. |
| `configs/iqm_surface_d3_baseline.yaml` | Native mapped d=3 IQM hardware baseline. |
| `configs/iqm_surface_d3_r1_native.yaml` | Shortest native d=3 hardware sanity check. |
| `configs/iqm_surface_d5_baseline.yaml` | Routed-layout d=5 IQM hardware baseline. |
| `configs/experiment_matrix.yaml` | Planning matrix only; not currently executed by `main.py`. |

## Noise Model

The same YAML block is used by Stim circuit generation:

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

Meaning by backend:

- Simulator: noise is inserted into the Stim circuit and affects samples.
- IQM hardware: Stim noise instructions are skipped during Qiskit conversion. The noise values only define the detector error model used by PyMatching.

Current mapping inside `qec_pipeline/codes/surface_code.py`:

```text
one_qubit_error     -> after_clifford_depolarization
measurement_error   -> before_measure_flip_probability
reset_error         -> after_reset_flip_probability
idle_error          -> before_round_data_depolarization
two_qubit_error     -> not separately used yet
```

Calibration data now first enters through mapping:

```text
full QPU per-qubit/per-coupler data
-> qec_pipeline/mapping/patch_selection.py
-> PRX/readout/QND/idle/CZ scoring
-> native patch or routed-layout initial_layout
-> IQM transpile
```

Later, the same calibration data should also drive decoder weights or a better detector error model.

## Hardware Path

For IQM runs:

```text
Stim circuit
-> qec_pipeline/conversion.py
-> Qiskit circuit
-> IQMProvider backend
-> Qiskit transpile
-> IQM job
-> counts
-> qec_pipeline.measurements.counts_to_measurement_array
-> syndrome extraction
```

Current hardware limitations:

- D3 has native calibration patch selection and now avoids poor QND/T2 qubits.
- D5 has routed calibration layout selection, not a perfect native patch.
- No QPU-specific calibration model yet.
- No pulse-level/PulLA path yet.
- Measurement order should be checked carefully for every new converter or backend change.
- `reset_mode: reset` is the only implemented reset behavior.

## Where New Work Should Plug In

Use these boundaries:

| New work | Add here | Must return |
| --- | --- | --- |
| Color code | `qec_pipeline/codes/color_code.py` | `(stim_circuit, detector_model, measurement_order, circuit_info)` |
| Better surface-code generator | `qec_pipeline/codes/surface_code.py` | Same circuit tuple |
| GNN decoder | `qec_pipeline/decoders/gnn_decoder.py` | Same decoder tuple as PyMatching |
| Ising decoder | `qec_pipeline/decoders/ising_decoder.py` | Same decoder tuple as PyMatching |
| Calibration model | `qec_pipeline/noise/` | Noise params, weighted detector model, or decoder weights |
| Custom mapping | `qec_pipeline/mapping/` and IQM backend | Mapping metadata and lower transpiled depth/SWAPs |
| Extra plots | `qec_pipeline/analysis/` or `scripts/` | Files under the run directory |

## MVP Definition of Done

Done:

- Simulator pipeline runs end to end.
- Noisy simulator + PyMatching produces decoded LER.
- IQM hardware path runs and saves artifacts.
- `memory_z` and `memory_x` can run in one config.
- Rounds sweeps can produce `ler_vs_rounds.png`.
- Real IQM calibration dumps can drive d=3 native mapping and d=5 routed layout.

Still needed for a stronger submission:

- Run d=5 routed layout on hardware and compare to the saturated d=5 baseline.
- Use selected layout metadata to reduce transpiled depth further.
- Compare at least two QPUs or two hardware patches.
- Generate calibrated simulator data for GNN training.
- Document every LER change with one changed variable at a time.
