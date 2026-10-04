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

Current calibrated d3 simulator sweep:

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

## Results

Result summaries live in [baselines/](baselines/), split by provenance. Raw `results/` runs are ignored and disposable.

> Simulator numbers produced before 2026-10-04 include the idle-noise scaling bug ([ERRATA.md E1](ERRATA.md#e1-calibrated-simulator-idle-noise-grows-with-the-square-of-the-round-count-critical)),
> which overstates the simulator LER for r ≥ 3. Corrected values are shown below.

### Hackathon (2026-06-07, d=3 rotated surface code, IQM Emerald, 2000 shots)

From [`baselines/hackathon_2026-06-07/`](baselines/hackathon_2026-06-07/):

| Rounds | Hardware memory_z | Hardware memory_x | Simulator memory_z (pre-fix) | Simulator memory_x (pre-fix) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.0490 | 0.0545 | 0.0210 | 0.0265 |
| 3 | 0.4870 | 0.4925 | 0.1675 | 0.2025 |
| 5 | 0.4840 | 0.4965 | 0.3670 | 0.3580 |
| 7 | 0.4720 | 0.4825 | 0.4680 | 0.4715 |

### Post-hackathon

From [`baselines/post_hackathon/`](baselines/post_hackathon/):

**Corrected simulator (2026-10-04, after the idle-noise fix, same configs as the hackathon runs):**

| Rounds | d3 memory_z | d3 memory_x | d5 memory_z (routed layout) |
| ---: | ---: | ---: | ---: |
| 1 | 0.0210 | 0.0265 | 0.047 |
| 3 | 0.0805 | 0.0940 | 0.128 |
| 5 | 0.1270 | 0.1530 | 0.206 |
| 7 | 0.1685 | 0.1975 | — |
| Error per round | ≈0.028 (constant) | ≈0.034 (constant) | ≈0.047–0.050 |

d3: 2000 shots, decoder candidates still selected in-sample (ERRATA E3). d5: 1000 shots, plain calibrated MWPM.
The simulator model itself is hand-tuned (ERRATA E2); hardware at r=1 is 0.049–0.059.

**Earlier post-hackathon work (2026-06-08):**

- **Hardware replication** (`iqm_baseline_replication_20260608`): the d=3 Emerald sweep reproduces the saturation (LER 0.48–0.50 for r ≥ 3).
- **Why it saturates:** in the raw data, the uncorrected logical observable flips with probability ≈0.5 for r ≥ 3 in both bases (≈0.13 at r=1). The data qubits are scrambled once mid-circuit measurement/reset begins ([ERRATA.md E5](ERRATA.md#e5-surface-code-hardware-runs-data-qubits-are-randomized-by-mid-circuit-measurereset)). Decoder changes cannot fix this.
- **Decoder experiments:** on the buggy June simulator, same-batch tuning looked better but holdout/k-fold did not confirm it (`decoder_validation_20260608`). On the corrected simulator (`decoder_validation_idlefix_20261004`), out-of-fold selection of correlated matching lowers the memory_x error per round from 0.035 to 0.030; memory_z is unchanged. These are simulator results only: on hardware the data is lost before decoding (E5).
- **Postselection** (`low_syndrome_postselection_20260608`, `best_combined_reported_20260608`, `iqm_best_combined_reported_20260608`) keeps only 25–60% of shots. It is a diagnostic, not a logical-memory result.
