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
provided/                  original challenge/reference code
results/                   generated run outputs
```

The active implementation is under `qec_pipeline/`. The old root-level starter files were moved to `provided/` so there is one clear code path.

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

Run the minimal IQM hardware baseline:

```bash
python main.py configs/iqm_surface_d3_baseline.yaml
```

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
- a small end-to-end pipeline run.

## Main Modules

```text
qec_pipeline/pipeline.py              orchestration
qec_pipeline/codes/surface_code.py    Stim circuit builder
qec_pipeline/conversion.py            Stim-to-Qiskit converter
qec_pipeline/measurements.py          Qiskit counts to measurement array
qec_pipeline/syndrome_extraction.py   raw measurements to detector events
qec_pipeline/decoders/                decoders
qec_pipeline/backends/                simulator and IQM runners
qec_pipeline/analysis/                metrics and artifact writing
```

## Current Limitations

- `surface_code` is the only implemented code family.
- `observable_rate` is only a sanity decoder.
- GNN, Ising, and color-code modules are placeholders.
- Hardware mapping is currently automatic through Qiskit/IQM.
- `reset_mode: no_reset` is not implemented.
- `two_qubit_error` is documented in configs but not separately mapped into the current Stim noise parameters yet.
