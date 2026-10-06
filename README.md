# QEC Pipeline

Surface-code memory experiments on IQM superconducting hardware: Stim circuits, a calibration-informed simulator, IQM execution, and matching decoders.

> **Hackathon vs. later work.** This project started as team *gate_crushers*' entry to the IQM QEC challenge at
> **Junction Quantum Hack 2026** (5–7 June 2026). The submission is frozen and is **not** what `main` contains today.
>
> | | Where |
> | --- | --- |
> | Hackathon submission (frozen) | tag `hackathon-submission-2026-06-07` (code), tag `junction-quantum-hackathon-final-2026` + [release](https://github.com/kazulak/JunctionHackathon/releases/tag/junction-quantum-hackathon-final-2026) (code + submitted zip and slides) |
> | Post-hackathon development | `main` (from 2026-06-08 onward) |
> | Timeline and verification | [PROVENANCE.md](PROVENANCE.md) |
> | Known issues in submitted and archived numbers | [ERRATA.md](ERRATA.md) |

Built on the challenge baseline provided by the organizers (see [NOTICE](NOTICE)). MIT licensed ([LICENSE](LICENSE)).

## Results: d = 3 surface-code memory on IQM Emerald

Logical error rate (LER) after r rounds, 2000 shots per point, calibrated MWPM decoder:

| Rounds | Hackathon (2026-06-07) memory_z / memory_x | Now (2026-10-04) memory_z | Now memory_x |
| ---: | ---: | ---: | ---: |
| 1 | 0.049 / 0.055 | 0.036 | 0.040 |
| 3 | 0.487 / 0.493 | 0.089 | 0.112 |
| 5 | 0.484 / 0.497 | 0.154 | 0.163 |
| 7 | 0.472 / 0.483 | 0.189 | 0.229 |
| Error per round | saturated (random output) | **0.033 ± 0.002** | **0.040 ± 0.002** |

In June the logical qubit was lost from round 2 onward. The cause was the circuit, not the decoder: readouts were not
multiplexed and each Qiskit `reset` added another measurement, so one round took 7.6 µs while the data qubits idled
without dynamical decoupling. The current design uses no mid-circuit reset (Gehér et al., arXiv:2408.00758),
grouped readout and IQM's native dynamical decoupling, which gives a 1.3 µs round. Details:
[docs/HARDWARE_RUNBOOK.md](docs/HARDWARE_RUNBOOK.md), data: [`baselines/post_hackathon/hw_d3_noreset_dd_20261004`](baselines/post_hackathon/hw_d3_noreset_dd_20261004/).

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt   # tests + lint
```

IQM credentials are read from `.env` (`IQM_TOKEN`) or the environment. Never commit `.env`.

## Run

```bash
python main.py configs/demo_stim_no_noise.yaml                                    # smoke test, LER 0
python scripts/sweep_rounds.py configs/hw_d3_noreset_dd_sim.yaml --rounds 1 7 4   # simulator twin of the hardware run
```

Hardware (read the runbook first; the preflight and Pulla report are free):

```bash
python scripts/fetch_calibration.py
python scripts/sweep_rounds.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 7 4 --preflight
python scripts/sweep_rounds.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 7 4
```

All configs: [configs/README.md](configs/README.md). How the pipeline works and how to extend it: [docs/PIPELINE.md](docs/PIPELINE.md).

## Layout

```text
main.py          run one config
configs/         experiment YAMLs; IQM calibration dumps in configs/calibration/
qec_pipeline/    pipeline implementation
scripts/         sweeps, hardware tools, analysis, archiving
tests/           regression tests (python -m unittest discover -s tests)
docs/            pipeline, simulator noise model, hardware runbook
baselines/       archived result summaries, split hackathon / post-hackathon
results/         generated outputs (ignored)
```

## Further results

[baselines/README.md](baselines/README.md) indexes every archived run with its date and provenance. Highlights:

- **Simulator.** The calibration-informed model predicted 0.039 (memory_z) / 0.059 (memory_x) error per round
  before the October hardware run ([`hw_d3_noreset_dd_prediction_20261004`](baselines/post_hackathon/hw_d3_noreset_dd_prediction_20261004/)).
- **Decoders.** On the simulator, choosing correlated matching by k-fold cross-validation lowers the error per round
  by 5–10 %; Google's p_ij decoder needs more than 2000 shots per circuit to help on hardware.
- **Postselection** keeps only 25–60 % of shots. It is a diagnostic, not a logical-memory result.
- **Hackathon simulator numbers** contain an idle-noise bug that overstates LER for r ≥ 3 ([ERRATA E1](ERRATA.md)).
