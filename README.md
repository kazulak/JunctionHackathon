# Junction QEC Pipeline

Offline quantum error correction pipeline for the IQM challenge.

Current runnable flow:

```text
YAML config
-> Stim surface-code circuit
-> Stim simulator or IQM hardware
-> raw measurements
-> detector events
-> decoder
-> logical error rate
```

## Layout

```text
main.py                    CLI entry point
configs/                   YAML experiment configs
qec_pipeline/              active pipeline implementation
tests/                     fast unit tests
scripts/                   visual inspection helpers
docs/                      pipeline notes
results/                   generated run outputs
archive/                   old/reference material not used by the pipeline
```

The active implementation is under `qec_pipeline/`. Reference notebooks, original challenge snippets, old notes, and unused experiments live under `archive/` so there is one clear runnable code path.

## Run

Create and use a Python 3.11 venv:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dry-run a config:

```bash
python main.py --dry-run --print-config configs/demo_stim_no_noise.yaml
```

Run the no-noise simulator smoke test:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Run the noisy simulator with PyMatching:

```bash
python main.py configs/demo_stim_simple_noise_pymatching.yaml
```

Run the IQM-calibrated Emerald simulator:

```bash
python main.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml
```

Run a calibrated simulator rounds sweep:

```bash
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml --rounds 1 5 3
```

Run the mapped IQM d=3 hardware baseline:

```bash
python main.py configs/iqm_surface_d3_baseline.yaml
```

Run the shortest native d=3 hardware sanity check:

```bash
python main.py configs/iqm_surface_d3_r1_native.yaml
```

Run the same one-round check without explicit initial reset gates:

```bash
python main.py configs/iqm_surface_d3_r1_no_initial_reset.yaml
```

Run the routed-layout IQM d=5 hardware baseline:

```bash
python main.py configs/iqm_surface_d5_baseline.yaml
```

Run a rounds sweep and plot LER:

```bash
python scripts/sweep_rounds.py configs/iqm_surface_d5_baseline.yaml --rounds 3 25 5
```

This writes `sweep_results.csv`, `sweep_results.json`, `summary.md`, and `ler_vs_rounds.png`.

For IQM, set exactly one auth source:

```powershell
$env:IQM_TOKEN="your-token"
```

Do not also put `backend.options.token` in YAML when `IQM_TOKEN` is set.

## Test

```bash
python -m unittest discover -s tests -v
```

Current tests cover:

- Stim-to-Qiskit translation,
- measurement-order conversion,
- config loading,
- surface-code circuit building,
- simulator backend,
- syndrome extraction,
- observable-rate and PyMatching decoders,
- artifact writing,
- rounds sweep plotting,
- calibration patch selection,
- a small end-to-end pipeline run.

## Main Modules

```text
qec_pipeline/pipeline.py              orchestration
qec_pipeline/codes/surface_code.py    Stim circuit builder
qec_pipeline/codes/surface_code_iqm.py calibration-first rotated surface-code builder
qec_pipeline/codes/surface_code_unrotated.py unrotated surface-code builder
qec_pipeline/conversion.py            Stim-to-Qiskit converter
qec_pipeline/measurements.py          Qiskit counts to measurement array
qec_pipeline/syndrome_extraction.py   raw measurements to detector events
qec_pipeline/decoders/                decoders
qec_pipeline/backends/                simulator and IQM runners
qec_pipeline/analysis/                metrics and artifact writing
qec_pipeline/mapping/                 QPU patch selection
qec_pipeline/noise/iqm_calibration.py per-qubit/per-coupler IQM noise injection
qec_pipeline/sweeps.py                rounds sweeps and LER plots
```

To add an alternative module, see [MODULE_INTEGRATION.md](docs/MODULE_INTEGRATION.md). New implementations are selected by YAML through small registries in `codes`, `decoders`, and `backends`.

## Current Limitations

- Implemented code families: `surface_code`, `surface_code_iqm`, `surface_code_unrotated`.
- `observable_rate` is only a sanity decoder.
- Implemented decoders: `observable_rate`, `pymatching`, `pymatching_calibrated`.
- GNN, Ising, and color-code modules are placeholders.
- `mapping.strategy: calibration_best_patch` can select a native d=3 patch from the real IQM observation dumps.
- `mapping.strategy: calibration_routed_layout` can choose a d=5 initial layout and let Qiskit route non-native edges.
- IQM mapping scores now include PRX, readout, QND, idle/T2, and CZ calibration terms.
- `reset_mode: no_reset` is not implemented.
- `noise.model: iqm_calibration` injects mapped PRX/readout/QND/idle/CZ errors into the Stim simulator and detector model.

## Calibrated Simulator Targets

Generated on June 7, 2026 with the Emerald calibration dump:

```text
d3 rotated, native mapped, rounds [1, 3, 5], 2000 shots:
memory_z LER: 0.168 -> 0.392 -> 0.490
memory_x LER: 0.1705 -> 0.397 -> 0.474
Plot: results/sim_iqm_emerald_surface_d3_calibrated_rounds_sweep/20260607T001653Z/ler_vs_rounds.png

d5 rotated, routed layout, rounds [1, 3, 5], 1000 shots:
memory_z LER: 0.307 -> 0.447 -> 0.501
Plot: results/sim_iqm_emerald_surface_d5_calibrated_rounds_sweep/20260607T001619Z/ler_vs_rounds.png
```

Interpretation: the current calibration model already predicts saturation by five rounds. If hardware is much worse at one round than these simulator targets, the missing piece is probably execution overhead/reset/readout behavior not captured by this simple Stim-level noise model.

## Reading LER Near 0.5

LER near `0.5` means the logical output is basically random. In the current pipeline this is now flagged in each basis folder as `diagnostics.json`.

Current hardware baseline, recorded on June 6, 2026:

```text
Config: d=5, rounds=5, memory_z, 1000 shots, IQM Emerald
Run: results/iqm_surface_d3_baseline/20260606T163211Z
LER: 0.504 +/- 0.0158
Detector saturation: 115 / 120 detectors near 0.5
Transpiled depth: 276 vs Qiskit depth 41
Two-qubit gates after transpilation: 842
```

Check these first:

- `diagnostics.json`: warnings, detector firing rates, transpilation depth ratio.
- `measurement_diagnostics.json`: per-measurement ideal vs observed one-rates, including hardware qubit labels when mapped.
- `raw_metadata.json`: original depth, transpiled depth, two-qubit gate count.
- `syndrome_metadata.json`: detector firing rates.

If most detectors fire near `0.5`, the issue is usually not the decoder alone. It is usually circuit depth/routing, hardware noise, bad mapping, or a measurement-order mismatch. For the latest saved d=5 hardware run, alternative bit-order decoding did not improve LER, while transpilation expanded the circuit heavily.

Latest mapped d=3 hardware result:

```text
Run: results/iqm_surface_d3_r1_native/20260606T193823Z
Code: d=3, rounds=1, memory_z + memory_x, 1000 shots, IQM Emerald
memory_z LER: 0.398 +/- 0.0155
memory_x LER: 0.435 +/- 0.0157
```

This one-round run is already too high. The saved data shows deterministic syndrome bits on some ancillas firing at `0.36-0.48`, so the next retest should use the updated converter that skips unused final ancilla resets and then inspect `measurement_diagnostics.json`.

The next A/B test is `configs/iqm_surface_d3_r1_no_initial_reset.yaml`. It removes explicit initial Qiskit reset gates and relies on the QPU shot initialization. If deterministic first-round syndrome bits improve, explicit reset/preparation was a major source of damage.

For the no-active-reset virtualized-record run, use:

```bash
python main.py configs/iqm_surface_d3_no_initial_reset.yaml
```

That config now omits both initial and repeated reset gates. Repeated ancilla measurements are converted into virtual reset-style records before Stim syndrome extraction.
It also pins the exact Stim-to-hardware assignment from the successful one-round run so graph-isomorphism tie-breaking cannot silently choose a different stabilizer layout.
Change `code.rounds` in that YAML when running a round-count A/B test.

Summarize the worst deterministic measurement failures after a run:

```bash
python scripts/summarize_measurement_diagnostics.py results/<experiment>/<timestamp> --top 8
```

Stress-test PyMatching weights on a saved hardware run:

```bash
python scripts/decoder_noise_sweep.py results/<experiment>/<timestamp>
```

Latest routed d=5 hardware result:

```text
Run: results/iqm_surface_d5_baseline/20260606T182846Z
Code: d=5, rounds=5, memory_z, 1000 shots, IQM Emerald
LER: 0.48 +/- 0.0158
Mean detector firing rate: 0.476
Saturated detectors: 112 / 120
Transpiled depth: 275
CZ gates after transpilation: 981
```

## Calibration Mapping

Calibration should enter the normal pipeline through `mapping`, not through a separate endpoint.

Native d=3 patch:

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
    exclude_qubits: [QB9, QB25, QB41, QB46, QB47]
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
    route_distance: 0.2
  options:
    seed: 1
    max_iterations: 5000
    exclude_qubits: [QB9, QB25, QB41, QB46, QB47]
```

Flow:

```text
full QPU calibration/topology
-> score native patch or routed layout
-> choose initial_layout
-> pass selected initial_layout to Qiskit transpile
-> run the normal pipeline
```

The selector uses per-qubit and per-coupler values. It does not average the whole QPU into one number.

Current offline d=5 Emerald routed-layout check:

```text
49 circuit qubits mapped
excluded bad qubits: QB9, QB25, QB41, QB46, QB47
50 / 80 unique code interactions are native
30 / 80 require routing
max hardware graph route distance: 5
```

Current real calibration files:

- `configs/2026-06-06T06_08_52.470451Z.json`: 54-qubit Emerald-like dump.
- `configs/2026-06-06T16_44_10.718568Z.json`: 20-qubit Garnet-like dump.
