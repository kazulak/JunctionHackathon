# Pipeline Steps

This document explains what happens in the current runnable pipeline.

## Commands

No-noise simulator:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

IQM-calibrated simulator with PyMatching:

```bash
python main.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml
```

Dry-run IQM hardware config:

```bash
python main.py --dry-run --print-config configs/iqm_surface_d3_r1_no_initial_reset.yaml
```

Run IQM hardware config:

```bash
python main.py configs/iqm_surface_d3_r1_no_initial_reset.yaml
```

Run the d=3 no-active-reset variant:

```bash
python main.py configs/iqm_surface_d3_r2_no_active_reset.yaml
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
- With `backend.options.batch_submit: true`, all circuits from `basis: both` or a hardware rounds sweep are submitted as one IQM batch before the pipeline waits for results.
- `MR`/`MRX` resets are kept only when that measured qubit is used again later; terminal unused resets are skipped before hardware execution.
- `backend.options.omit_initial_resets: true` additionally skips leading explicit Qiskit reset gates for hardware A/B tests; later repeated-round resets remain.
- `backend.options.omit_repeated_resets: true` skips repeated syndrome reset gates and XOR-converts repeated ancilla records into virtual reset-style measurements before decoding.
- If `mapping.strategy: calibration_best_patch`, full QPU calibration is used to choose `initial_layout` before transpile.
- If `mapping.strategy: calibration_routed_layout`, full QPU calibration is used to choose a low-cost routed `initial_layout` before transpile.
- If `mapping.strategy: none`, Qiskit/IQM chooses layout and routing.

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
measurement_diagnostics.json
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

For `sim_iqm_emerald_surface_d3_calibrated.yaml`:

- Detection events should be nonzero.
- LER should be low at one round and increase with rounds.
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
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml --rounds 1 5 3
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
python scripts/sweep_rounds.py configs/iqm_surface_d3_r1_no_initial_reset.yaml --rounds 1 3 3 --dry-run
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

Current recorded baseline:

```text
Run: results/iqm_surface_d3_baseline/20260606T163211Z
Code: d=5, rounds=5, memory_z
Shots: 1000
LER: 0.504 +/- 0.0158
Mean detector firing rate: 0.488
Saturated detectors: 115 / 120
Transpiled depth: 276 vs Qiskit depth 41
Two-qubit gates after transpilation: 842
```

This proves the hardware path works, but the syndrome data is nearly random. Treat this as the baseline to beat, not as successful error correction.

## Calibration Mapping

Enable native d=3 patch selection in the normal experiment config:

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
```

D5 uses routed layout selection instead:

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

What happens:

```text
Stim surface-code circuit
-> real QPU calibration/topology
-> score native patches or routed layouts
-> choose lowest-score initial_layout
-> pass initial_layout to Qiskit transpile
```

This is not an average over the QPU. It uses spatial calibration data to find the best region.

Current real files:

```text
configs/2026-06-06T06_08_52.470451Z.json     54-qubit Emerald-like dump
configs/2026-06-06T16_44_10.718568Z.json     20-qubit Garnet-like dump
```

Current native-patch check:

```text
d=3 on Emerald dump: works, 64 native candidates
d=3 on Garnet dump: works, 4 native candidates
d=5 on Emerald dump: no native surface-code graph found
```

Current routed-layout d=5 Emerald check:

```text
49 circuit qubits mapped
excluded bad qubits: QB9, QB25, QB41, QB46, QB47
50 / 80 unique code interactions are native
30 / 80 require routing
max hardware graph route distance: 5
```

This is not a perfect d=5 patch. It is a better initial layout for Qiskit than blind routing.

## Where QPU Calibration Fits

Placement path implemented now:

```text
IQM QPU calibration numbers
-> mapping.calibration_file
-> native patch score or routed layout score
-> Qiskit initial_layout
```

Simple decoder-model path implemented now:

```text
YAML noise.parameters
-> Stim detector error model
-> PyMatching weights
```

Better decoder-model path to implement:

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
