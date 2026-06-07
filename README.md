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

Judge-facing summary: [docs/JUDGE_SUMMARY.md](docs/JUDGE_SUMMARY.md).

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

Run the current paired Emerald d=3 simulator sweep:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_sim.yaml --rounds 1 7 4
```

Run the matching IQM hardware sweep. The config uses IQM batch submission, so all sweep circuits are submitted before waiting for results:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_iqm.yaml --rounds 1 7 4
```

Run the postselected simulator/hardware pair:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_postselected_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_postselected_iqm.yaml --rounds 1 7 4
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
- Implemented decoders: `observable_rate`, `pymatching`, `pymatching_calibrated`, `pymatching_auto`.
- `pymatching_auto` can try calibrated/uniform MWPM weights, no-correction, and optional syndrome-weight postselection.
- GNN, Ising, and color-code modules are placeholders.
- `mapping.strategy: calibration_best_patch` can select a native d=3 patch from the real IQM observation dumps.
- `mapping.strategy: calibration_routed_layout` can choose a d=5 initial layout and let Qiskit route non-native edges.
- IQM mapping scores now include PRX, readout, QND, idle/T2, and CZ calibration terms.
- `reset_mode: no_reset` is not implemented.
- `noise.model: iqm_calibration` injects mapped PRX/readout/QND/idle/CZ errors into the Stim simulator and detector model.

## Current Results

Generated on June 7, 2026 with the Emerald calibration dump and the pinned d=3 native patch.

Normal calibrated simulator, `configs/sweep_d3_best_sim.yaml`, 2000 shots:

```text
rounds 1: memory_z 0.021 +/- 0.0032, memory_x 0.0265 +/- 0.0036
rounds 3: memory_z 0.1675 +/- 0.0083, memory_x 0.2025 +/- 0.0090
rounds 5: memory_z 0.367 +/- 0.0108, memory_x 0.358 +/- 0.0107
rounds 7: memory_z 0.468 +/- 0.0112, memory_x 0.4715 +/- 0.0112
artifact: results/sweep_d3_best_sim_rounds_sweep/20260607T011525Z
```

Matching IQM hardware sweep, `configs/sweep_d3_best_iqm.yaml`, 2000 shots:

```text
rounds 1: memory_z 0.049 +/- 0.0048, memory_x 0.0545 +/- 0.0051
rounds 3: memory_z 0.487 +/- 0.0112, memory_x 0.4925 +/- 0.0112
rounds 5: memory_z 0.484 +/- 0.0112, memory_x 0.4965 +/- 0.0112
rounds 7: memory_z 0.472 +/- 0.0112, memory_x 0.4825 +/- 0.0112
artifact: results/sweep_d3_best_iqm_rounds_sweep/20260607T011549Z
```

Postselected calibrated simulator, `configs/sweep_d3_postselected_sim.yaml`, keeps about half of shots with lowest syndrome weight:

```text
rounds 1: memory_z 0.0, memory_x 0.0
rounds 3: memory_z 0.0929 +/- 0.0089, memory_x 0.1028 +/- 0.0095
rounds 5: memory_z 0.3135 +/- 0.0136, memory_x 0.3211 +/- 0.0135
rounds 7: memory_z 0.4538 +/- 0.0142, memory_x 0.4650 +/- 0.0157
artifact: results/sweep_d3_postselected_sim_rounds_sweep/20260607T012558Z
```

Active model knobs:

```yaml
noise:
  options:
    qnd_scale: 0.0
    idle_scale: 0.5
```

Interpretation: one-round hardware is now close enough to the simulator to be useful, but hardware saturates immediately from round 3. The likely missing pieces are repeated-round reset/readout dynamics, circuit timing, leakage, crosstalk, and pulse-level compilation effects that are not captured by the current Stim-level calibration model.

## Reading LER Near 0.5

LER near `0.5` means the logical output is basically random. In this pipeline each basis folder writes:

- `diagnostics.json`: warning summary.
- `measurement_diagnostics.json`: per-measurement ideal vs observed one-rates, with hardware qubit labels when mapped.
- `raw_metadata.json`: job ID, circuit depths, operation counts, transpiler metadata.
- `syndrome_metadata.json`: detector firing rates and mean syndrome weight.
- `metrics.json`: LER, uncertainty, logical failures, and `decoder_info`.

If most detectors fire near `0.5`, treat it as a circuit/noise/execution problem before blaming the decoder. The current symptom is precise: round 1 works, but rounds 3+ saturate on hardware while the simulator degrades more gradually.

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
