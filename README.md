# QEC Pipeline

Simulator-first quantum error-correction pipeline for surface-code experiments.

The hackathon submission is preserved at:

```text
branch: checkpoint/junction-quantum-hackathon-final
tag:    junction-quantum-hackathon-final-2026
```

Current development goal: get meaningful LER improvements in simulation first, then spend IQM credits only on configs that already look promising locally.

## Flow

```text
YAML config
-> Stim circuit
-> simulator or IQM hardware
-> raw measurements
-> detector events
-> decoder
-> LER + artifacts
```

## Layout

```text
main.py                    run one config
configs/                   experiment YAMLs and IQM calibration dumps
qec_pipeline/              pipeline implementation
scripts/                   sweeps and visual checks
tests/                     regression tests
docs/                      short notes for configs/modules/simulation
baselines/                 tracked compact baseline summaries
results/                   ignored generated outputs
```

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

Smoke test:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Current calibrated d3 simulator sweep:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_sim.yaml --rounds 1 7 4
```

Postselection simulator experiment:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_postselected_sim.yaml --rounds 1 7 4
```

Best combined reported-LER simulator experiment:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_combined_sim.yaml --rounds 1 7 4
```

Full-shot decoder improvement experiment:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_decoder_improvements_sim.yaml --rounds 1 7 4
```

Out-of-fold decoder validation:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_decoder_kfold_sim.yaml --rounds 1 7 4
```

D5 calibrated simulator:

```bash
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d5_calibrated.yaml --rounds 1 5 3
```

Only after a simulator result is worth checking, dry-run the best combined hardware config:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_combined_iqm.yaml --rounds 1 7 4 --dry-run
```

Then run the IQM sweep:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_combined_iqm.yaml --rounds 1 7 4
```

IQM auth is loaded from `.env` or the shell environment. Do not commit `.env`.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests cover config loading, Stim-to-Qiskit translation, measurement conversion, syndrome extraction, decoders, simulator runs, artifacts, sweeps, and calibration patch selection.

## Main Configs

```text
configs/demo_stim_no_noise.yaml
configs/sweep_d3_best_sim.yaml
configs/sweep_d3_postselected_sim.yaml
configs/sweep_d3_best_combined_sim.yaml
configs/sweep_d3_best_combined_iqm.yaml
configs/sweep_d3_decoder_improvements_sim.yaml
configs/sweep_d3_decoder_kfold_sim.yaml
configs/sim_iqm_emerald_surface_d3_calibrated.yaml
configs/sim_iqm_emerald_surface_d3_unrotated_calibrated.yaml
configs/sim_iqm_emerald_surface_d5_calibrated.yaml
configs/sweep_d3_best_iqm.yaml
```

Details: [configs/README.md](configs/README.md).
Research workflow: [docs/RESEARCH_ROADMAP.md](docs/RESEARCH_ROADMAP.md).

## Main Modules

```text
qec_pipeline/pipeline.py              orchestration
qec_pipeline/codes/                   Stim circuit builders
qec_pipeline/backends/                simulator and IQM runners
qec_pipeline/decoders/                observable_rate, PyMatching, auto route
qec_pipeline/noise/iqm_calibration.py calibrated Stim noise
qec_pipeline/mapping/                 calibration-driven patch/layout selection
qec_pipeline/analysis/                artifacts and reports
qec_pipeline/sweeps.py                LER-vs-rounds sweeps
```

Adding modules: [docs/MODULE_INTEGRATION.md](docs/MODULE_INTEGRATION.md).

## Visual Checks

```bash
python scripts/plot_stim_circuit.py results/<experiment>/<timestamp>
python scripts/plot_qiskit_translation.py results/<experiment>/<timestamp>
```

## Current Baseline

The surface-code pipeline works, but real hardware repeated rounds saturated during the hackathon.

Compact preserved files live in [baselines/](baselines/). Raw `results/` runs are ignored and disposable.

Recorded d3 calibrated simulator, 2000 shots:

```text
rounds 1: memory_z 0.0210, memory_x 0.0265
rounds 3: memory_z 0.1675, memory_x 0.2025
rounds 5: memory_z 0.3670, memory_x 0.3580
rounds 7: memory_z 0.4680, memory_x 0.4715
```

Same-batch decoder candidate tuning looked better, 2000 shots:

```text
rounds 1: memory_z 0.0210, memory_x 0.0265
rounds 3: memory_z 0.1645, memory_x 0.1995
rounds 5: memory_z 0.3585, memory_x 0.3470
rounds 7: memory_z 0.4585, memory_x 0.4605
```

But held-out and k-fold validation did not confirm the improvement. Treat same-batch decoder tuning as diagnostic only, not a deployable result.

Recorded k-fold decoder validation, 2000 shots:

```text
rounds 1: memory_z 0.0210, memory_x 0.0265
rounds 3: memory_z 0.1645, memory_x 0.2005
rounds 5: memory_z 0.3640, memory_x 0.3550
rounds 7: memory_z 0.4890, memory_x 0.4795
```

Best combined reported-LER simulator route, 2000 original shots:

```text
rounds 1: memory_z 0.0000, memory_x 0.0000
rounds 3: memory_z 0.0650, memory_x 0.0697
rounds 5: memory_z 0.2562, memory_x 0.2644
rounds 7: memory_z 0.4239, memory_x 0.4463
```

This uses postselection and keeps about 25-56% of shots depending on round count.

Recorded matching IQM hardware, 2000 shots:

```text
rounds 1: memory_z 0.0490, memory_x 0.0545
rounds 3: memory_z 0.4870, memory_x 0.4925
rounds 5: memory_z 0.4840, memory_x 0.4965
rounds 7: memory_z 0.4720, memory_x 0.4825
```

Treat this as the starting point, not the result. For hardware, prefer the combined config if the goal is lowest reported LER; prefer the baseline config if the goal is full-shot comparison.
