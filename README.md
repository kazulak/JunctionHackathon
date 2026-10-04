# QEC Pipeline

Simulator-first quantum error-correction pipeline for surface-code memory experiments on IQM hardware.

> **Hackathon vs. later work.** This project started as team *gate_crushers*' entry to the IQM QEC challenge at
> **Junction Quantum Hack 2026** (5–7 June 2026). The submission is frozen and is **not** what `main` contains today.
>
> | | Where |
> | --- | --- |
> | Hackathon submission (frozen) | tag `hackathon-submission-2026-06-07` (code), tag `junction-quantum-hackathon-final-2026` + [release](https://github.com/kazulak/JunctionHackathon/releases/tag/junction-quantum-hackathon-final-2026) (code + submitted zip and slides) |
> | Post-hackathon development | `main` (from 2026-06-08 onward) |
> | Timeline, verification, credits | [PROVENANCE.md](PROVENANCE.md) |
> | Known issues in submitted and archived numbers | [ERRATA.md](ERRATA.md) |

Built on the challenge baseline provided by the organizers (see [NOTICE](NOTICE)).

Current development goal: understand why mid-circuit measure/reset destroys the data on IQM hardware (see [ERRATA.md](ERRATA.md) E5), then improve LER in simulation and spend IQM credits only on configs that look promising locally.

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
baselines/                 tracked result summaries, split hackathon / post-hackathon
results/                   ignored generated outputs
```

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt   # tests + lint
```

Optional GNN experiments: `requirements-gnn.txt`.

## Run

Smoke test:

```bash
python main.py configs/demo_stim_no_noise.yaml
```

Current d3 simulator sweep (calibration-informed noise fitted to r=1 hardware):

```bash
python scripts/sweep_rounds.py configs/sweep_d3_baseline_sim.yaml --rounds 1 7 4
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

D5 simulator (routed layout):

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
configs/sweep_d3_baseline_sim.yaml
configs/sweep_d3_postselected_sim.yaml
configs/sweep_d3_best_combined_sim.yaml
configs/sweep_d3_best_combined_iqm.yaml
configs/sweep_d3_decoder_improvements_sim.yaml
configs/sweep_d3_decoder_kfold_sim.yaml
configs/sim_iqm_emerald_surface_d3_calibrated.yaml
configs/sim_iqm_emerald_surface_d3_unrotated_calibrated.yaml
configs/sim_iqm_emerald_surface_d5_calibrated.yaml
configs/sweep_d3_baseline_iqm.yaml
```

Details: [configs/README.md](configs/README.md).
Research workflow: [docs/RESEARCH_ROADMAP.md](docs/RESEARCH_ROADMAP.md).

## Main Modules

```text
qec_pipeline/pipeline.py              orchestration
qec_pipeline/codes/                   Stim circuit builders
qec_pipeline/backends/                simulator and IQM runners
qec_pipeline/decoders/                observable_rate, PyMatching, auto route
qec_pipeline/noise/iqm_calibration.py calibration-informed Stim noise
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

## Results

Result summaries live in [baselines/](baselines/), split by provenance. Raw `results/` runs are ignored and disposable.

> Simulator numbers produced before 2026-10-04 (including the hackathon table below) include the idle-noise scaling bug
> ([ERRATA.md E1](ERRATA.md#e1-calibrated-simulator-idle-noise-grows-with-the-square-of-the-round-count-critical)),
> which overstates the simulator LER for r ≥ 3.

### Hackathon (2026-06-07, d=3 rotated surface code, IQM Emerald, 2000 shots)

From [`baselines/hackathon_2026-06-07/`](baselines/hackathon_2026-06-07/):

| Rounds | Hardware memory_z | Hardware memory_x | Simulator memory_z (pre-fix) | Simulator memory_x (pre-fix) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.0490 | 0.0545 | 0.0210 | 0.0265 |
| 3 | 0.4870 | 0.4925 | 0.1675 | 0.2025 |
| 5 | 0.4840 | 0.4965 | 0.3670 | 0.3580 |
| 7 | 0.4720 | 0.4825 | 0.4680 | 0.4715 |

### Post-hackathon

From [`baselines/post_hackathon/`](baselines/post_hackathon/). Each folder README states when and how it was produced.

**1. Hardware: mid-circuit operations destroy the data.**
A post-hackathon replication on IQM Emerald (`iqm_baseline_replication_20260608`) reproduces the saturation (LER 0.48–0.50 for r ≥ 3).
In the raw data the *uncorrected* logical observable already flips with probability ≈0.5 for r ≥ 3 in both bases (≈0.13 at r = 1):
the data qubits are scrambled once mid-circuit measure/reset begins ([ERRATA E5](ERRATA.md#e5-surface-code-hardware-runs-data-qubits-are-randomized-by-mid-circuit-measurereset), [`midcircuit_diagnosis_20261004`](baselines/post_hackathon/midcircuit_diagnosis_20261004/)).
No decoder can fix this. A probe experiment to find the cause is ready and needs IQM credits ([roadmap](docs/RESEARCH_ROADMAP.md)).

**2. Reference simulator (2026-10-04).**
This run includes the idle-noise fix and calibration noise fitted to r = 1 hardware ([`noise_fit_targets_r1`](baselines/post_hackathon/noise_fit_targets_r1/)), decoded with plain calibrated MWPM:

| Rounds | d3 memory_z | d3 memory_x | d5 memory_z (routed) |
| ---: | ---: | ---: | ---: |
| 1 | 0.047 | 0.083 | 0.099 |
| 3 | 0.180 | 0.219 | 0.325 |
| 5 | 0.263 | 0.321 | 0.452 |
| 7 | 0.339 | 0.400 | — |
| Fitted error per round | 0.068 ± 0.002 | 0.092 ± 0.003 | 0.141 ± 0.006 |

Hardware at r = 1 is 0.049–0.059 (memory_z) and 0.055–0.061 (memory_x). For r ≥ 2 the table shows what the model predicts *if* mid-circuit operations worked. The routed d5 layout is above threshold.

**3. Decoders** ([`decoder_and_postselection_fitted_noise_20261004`](baselines/post_hackathon/decoder_and_postselection_fitted_noise_20261004/)).
Choosing correlated matching by k-fold cross-validation lowers the error per round:

| Error per round | memory_z | memory_x |
| --- | ---: | ---: |
| Plain MWPM | 0.068 | 0.092 |
| k-fold selection (correlated matching) | 0.064 | 0.083 |

Selecting candidates in-sample looks slightly better still; that extra is selection bias. These are simulator results only.

**4. Postselection** keeps only 25–60% of shots. It is a diagnostic, not a logical-memory result.

Superseded post-hackathon results (June 2026, and the intermediate idle-fix-only re-runs) stay in `baselines/post_hackathon/` for transparency. Their READMEs point to what replaced them.
