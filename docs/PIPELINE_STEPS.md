# Pipeline Steps

This document explains what happens in the current runnable pipeline.

## Commands

No-noise simulator:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Noisy simulator with PyMatching:

```bash
python main.py configs/demo_stim_simple_noise_pymatching.yaml
```

Dry-run IQM hardware config:

```bash
python main.py --dry-run --print-config configs/iqm_surface_d3_baseline.yaml
```

Run IQM hardware config:

```bash
python main.py configs/iqm_surface_d3_baseline.yaml
```

## Stage By Stage

### 1. Load YAML

File:

```text
qec_pipeline/config.py
```

Input:

```text
configs/*.yaml
```

Output:

```text
normal Python dict
```

No dataclass or hidden state is used.

### 2. Choose basis

File:

```text
qec_pipeline/pipeline.py
```

Rules:

```text
basis: memory_z -> run memory_z
basis: memory_x -> run memory_x
basis: both     -> run memory_z, then memory_x
```

Each basis gets its own result folder.

### 3. Build Stim circuit

File:

```text
qec_pipeline/codes/surface_code.py
```

Function:

```text
build_surface_code_circuit(code, noise, basis)
```

Output:

```text
(stim_circuit, detector_model, measurement_order, circuit_info)
```

What it does:

- Uses `stim.Circuit.generated`.
- Builds `surface_code:rotated_memory_z` or `surface_code:rotated_memory_x`.
- Applies configured Stim noise for simulator and detector-model construction.
- Builds `detector_model = stim_circuit.detector_error_model(decompose_errors=True)`.

Important:

- The Stim circuit is the source of truth for detector definitions and logical observables.
- `reset_mode` is not branching behavior yet.
- `two_qubit_error` is not separately used yet.

### 4A. Run simulator backend

File:

```text
qec_pipeline/backends/simulator.py
```

Function:

```text
run_simulator_backend(backend, circuit)
```

Output:

```text
(measurements, counts, raw_info)
```

What it does:

- Calls `stim_circuit.compile_sampler`.
- Samples `backend.shots`.
- Returns a boolean raw measurement matrix.
- `counts` is `None` for simulator runs.

### 4B. Run IQM hardware backend

File:

```text
qec_pipeline/backends/iqm_hardware.py
```

Function:

```text
run_iqm_hardware_backend(backend, circuit)
```

Output:

```text
(measurements, counts, raw_info)
```

What it does:

```text
Stim circuit
-> qec_pipeline/conversion.py
-> Qiskit circuit
-> IQMProvider
-> Qiskit transpile
-> IQM backend run
-> Qiskit counts
-> qec_pipeline.measurements.counts_to_measurement_array
```

Important:

- Stim noise instructions are skipped during Qiskit conversion.
- Real QPU noise comes from hardware, not from YAML.
- YAML noise is still used by the Stim detector error model for PyMatching.
- Current mapping is automatic Qiskit/IQM mapping.

### 5. Extract detector events

File:

```text
qec_pipeline/syndromes.py
qec_pipeline/syndrome_extraction.py
```

Function:

```text
extract_detection_events(circuit, raw)
```

Output:

```text
(detection_events, observable_flips, syndrome_info)
```

What it does:

- Uses `qec_pipeline/syndrome_extraction.py`.
- Calls Stim `compile_m2d_converter()`.
- Converts raw measurement rows into detector events.
- Also extracts observable flips.

Shapes:

```text
measurements:      (shots, num_measurements)
detection_events:  (shots, num_detectors)
observable_flips:  (shots, num_observables)
```

Important:

- Raw measurements are not the decoder input.
- `detection_events` are the decoder input.
- `observable_flips` are used to score whether the decoder was right.

### 6A. Observable-rate sanity decoder

File:

```text
qec_pipeline/decoders/observable_decoder.py
```

This is only a sanity check.

It counts observed logical flips directly. It does not use the syndrome to correct anything.

### 6B. PyMatching decoder

File:

```text
qec_pipeline/decoders/pymatching_decoder.py
```

Function:

```text
decode_with_pymatching(decoder, circuit, syndromes)
```

Output:

```text
(predicted_observables, logical_failures, ler, uncertainty, decoder_info)
```

What it does:

```text
detector_model -> pymatching.Matching.from_detector_error_model
detection_events -> matching.decode_batch
predicted_observables XOR observable_flips -> logical_failures
mean(logical_failures) -> LER
sqrt(LER * (1 - LER) / shots) -> uncertainty
```

This is the current real decoder.

### 7. Write artifacts

File:

```text
qec_pipeline/analysis/reports.py
```

Output location:

```text
results/<experiment>/<timestamp>/
```

Per basis:

```text
memory_z/
memory_x/
```

Files:

```text
circuit.stim
circuit_metadata.json
raw_metadata.json
syndrome_metadata.json
metrics.json
diagnostics.json
raw_measurements_head.csv
detection_events_head.csv
observable_flips_head.csv
counts.json                 # hardware only
qiskit_circuit.txt          # hardware only
transpiled_circuit.txt      # hardware only
```

Top-level:

```text
summary.md
```

## Expected Results

For `demo_stim_no_noise.yaml`:

- Detection events should be all zero.
- Observable flips should be all zero.
- Logical failures should be zero.
- LER should be `0.0`.

For `demo_stim_simple_noise_pymatching.yaml`:

- Detection events should be nonzero.
- LER should be nonzero but small for the current low noise.
- Exact value changes with shots and seed.

For IQM hardware:

- Detection events should usually be nonzero.
- Detector firing rates should not all be zero.
- Detector firing rates should not all be near `0.5`; that suggests ordering/model mismatch or too much noise.
- LER must be interpreted with shot-count uncertainty.

## Visual Checks

Plot the saved Stim circuit:

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
```

Write Qiskit translation views:

```bash
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp>
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp> --png
```

Use these to compare:

- `circuit.stim`
- `qiskit_circuit.txt`
- `transpiled_circuit.txt`

The Qiskit converter is `qec_pipeline/conversion.py`. It supports memory-X instructions such as `RX`, `MX`, and `MRX`.

## Translation Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The tests check:

- generated surface-code metadata matches after conversion,
- Qiskit counts are converted back into Stim measurement order,
- `MR` and `MRX` reset semantics match Stim,
- `MX` preserves X-basis post-measurement state when a qubit is reused,
- unsupported inverted measurement targets fail loudly.

## Rounds Sweep Plot

Run:

```bash
python scripts/sweep_rounds.py configs/iqm_surface_d3_baseline.yaml --rounds 3 15 6
```

The three numbers mean:

```text
START STOP POINTS
```

Example:

```text
3 15 6 -> [3, 5, 8, 10, 13, 15]
```

Outputs:

```text
results/<experiment>_rounds_sweep/<timestamp>/sweep_results.csv
results/<experiment>_rounds_sweep/<timestamp>/sweep_results.json
results/<experiment>_rounds_sweep/<timestamp>/summary.md
results/<experiment>_rounds_sweep/<timestamp>/ler_vs_rounds.png
```

Use `--dry-run` before sending hardware jobs:

```bash
python scripts/sweep_rounds.py configs/iqm_surface_d3_baseline.yaml --rounds 3 15 6 --dry-run
```

## LER Near 0.5

LER near `0.5` means logical outcomes are basically random. For each future basis run, inspect:

```text
diagnostics.json
raw_metadata.json
syndrome_metadata.json
```

Useful warning signs:

- detector firing rates close to `0.5`,
- mean detector firing rate above roughly `0.25`,
- transpiled depth much larger than Qiskit depth,
- many transpiled `cz` or `cx` gates.

## Where QPU Calibration Fits

Current temporary path:

```text
IQM QPU calibration numbers
-> YAML noise.parameters
-> Stim detector error model
-> PyMatching weights
```

Better path to implement:

```text
IQM calibration table
-> qec_pipeline/noise/iqm_calibration.py
-> per-qubit/per-coupler error assumptions
-> better detector error model or decoder weights
-> PyMatching
```

Do not put calibration logic inside the hardware backend. The backend should run circuits and return measurements. The error model should be a separate module.

## Where Colleague Work Fits

| Work | Input | Output |
| --- | --- | --- |
| GNN decoder | `detection_events`, detector graph/features | decoder tuple |
| Color code | config code/noise/basis | circuit tuple |
| Ising decoder | detector events and compatible model | decoder tuple |
| Better mapping | Qiskit circuit, QPU topology | transpiled circuit + mapping metadata |
| Better reports | saved artifacts | plots/tables/Markdown |

Keep the pipeline contract unchanged unless absolutely necessary.

## Debug Checklist

When a result looks strange, check in this order:

1. `circuit_metadata.json`: measurement/detector/observable counts.
2. `raw_metadata.json`: backend, job ID, circuit depths, operation counts.
3. `raw_measurements_head.csv`: raw rows have expected width.
4. `detection_events_head.csv`: syndromes are not all broken.
5. `syndrome_metadata.json`: detector firing rates and mean syndrome weight.
6. `metrics.json`: failures, shots, LER, uncertainty.
7. `transpiled_circuit.txt`: depth and unexpected routing.
