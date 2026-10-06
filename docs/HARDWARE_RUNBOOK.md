# Hardware runbook: d3 surface-code memory on IQM Emerald

How to run the pipeline on real hardware with a small credit budget (IQM Resonance Starter: 30 credits, about 30 QPU seconds per month).

## What was wrong in June, and what changed

The June hardware runs lost all logical information from round 2 onward (ERRATA E5). Compiling the June circuits with IQM's own pulse compiler (`scripts/pulla_schedule_report.py`, no credits) against the live Emerald calibration showed why:

| | Extra time per syndrome round |
| --- | ---: |
| June circuits: `measure, reset, measure, reset, ...` per ancilla | 7.6 µs |
| Readouts grouped into one multiplexed block, Qiskit `reset` | 5.8 µs |
| Grouped + feed-forward conditional X (`code.mid_circuit_reset: feedforward`) | 1.75 µs |
| Grouped + no reset (`code.mid_circuit_reset: none`) | **1.3 µs** |

- IQM only multiplexes measurements that are adjacent with nothing in between on the same qubits. The June converter interleaved `reset` after every measurement, so the readouts ran one after another.
- On IQM a Qiskit `reset` is a second measurement plus a feedback pulse (`reset_conditional`).
- During those 7.6 µs the data qubits idled without dynamical decoupling. Ramsey T2 is ~15 µs median, so they decohered.
- Between shots IQM waited ~400 µs for qubits to relax, which made each shot ~0.4 ms of paid QPU time.

The pipeline now:

1. Encodes the reset strategy in the Stim circuit. With no reset (or feed-forward), detectors compare ancilla outcomes two rounds apart and readout errors form two-round edges (Gehér et al., arXiv:2408.00758). The decoder model is correct for each strategy.
2. Groups every measurement layer between barriers, so IQM reads them out in one ~1 µs window.
3. Uses IQM's native dynamical decoupling (`dynamical_decoupling: true`), as Google did for data qubits during readout (arXiv:2207.06431).
4. Keeps IQM's passive reset between shots. Active reset (`active_reset_cycles`) is ~25× cheaper per shot, but on 2026-10-04 it left ~10–20% initialization error, so it is **off** (`baselines/post_hackathon/hw_controls_reset_dd_20261004`).
5. Uses today's calibration (`scripts/fetch_calibration.py`) and refuses to submit if the QPU has been recalibrated since, plus per-shot memory, recorded physical qubits, and a layout guard.

## Before spending credits (all free)

```bash
python scripts/fetch_calibration.py                              # current calibration -> configs/calibration/
python scripts/sweep_rounds.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 2 --preflight
python scripts/pulla_schedule_report.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 5 7 \
    --dd --shots 2000                                            # schedule length per shot
python scripts/sweep_rounds.py configs/hw_d3_noreset_dd_sim.yaml --rounds 1 9 5   # simulator twin
```

If the calibration file changes, update `calibration_file` in both `hw_d3_noreset_dd_*` configs and rerun the preflight. Patch selection on a new calibration:

```bash
python scripts/select_patch.py configs/hw_d3_noreset_dd_iqm.yaml --calibration configs/calibration/<file>.json
```

The October 2026 calibration still ranks the June patch (QB13–QB45) best among 60 native d=3 patches.

## Prediction (archived before any new hardware run)

`baselines/post_hackathon/hw_d3_noreset_dd_prediction_20261004` (simulator twin, 20k shots):

| Rounds | memory_z LER | memory_x LER |
| ---: | ---: | ---: |
| 1 | 0.015 | 0.027 |
| 3 | 0.082 | 0.127 |
| 5 | 0.148 | 0.214 |
| 9 | 0.246 | 0.329 |
| Error per round | 0.039 | 0.059 |

June hardware gave 0.49 at r = 3.

## What happened on 2026-10-04 (5 jobs, ~12.3 s of QPU execution in total)

| Job | What | Outcome |
| --- | --- | --- |
| Pilot | r = 1, 3, both bases, active reset + DD | Failed at r = 1 (LER 0.29): active reset leaves qubits excited |
| Controls A/B/C | r = 1, memory_z: active/passive × DD on/off | Passive reset fixes it: LER 0.027; DD neutral at r = 1 |
| **Main sweep** | r = 1, 3, 5, 7, both bases, passive reset + DD, 2000 shots | **ε = 0.033 (Z), 0.040 (X) per round**; r = 3 LER 0.089 / 0.112 vs 0.49 in June |

Archives: `hw_pilot_noreset_dd_activereset_20261004`, `hw_controls_reset_dd_20261004`, `hw_d3_noreset_dd_20261004`.

## Cost model (measured)

- Each job carries **~0.6–0.8 s of fixed QPU execution** and ~3 s end to end.
- With passive reset each shot costs ~0.41 ms of schedule (≈0.5 ms measured), so 16 000 shots ≈ 8 s of execution.
- Prefer few large jobs. One sweep job (all rounds × both bases) is much cheaper than many small ones.
- Check the exact credits charged in the Resonance dashboard (Jobs).

## Suggested next experiments

| Experiment | Command | Shots | ~QPU s | Question |
| --- | --- | --- | ---: | --- |
| DD effect at depth | main sweep with `--set backend.options.dynamical_decoupling=false`, `--rounds 3 7 2` | 4 × 2000 | 4–5 | The model predicts DD roughly halves memory_x error per round |
| Feed-forward vs no reset | `--set code.mid_circuit_reset=feedforward --set noise.options.round_duration_s=1.75e-6`, `--rounds 3 7 2` | 4 × 2000 | 4–5 | Do conditional resets help or hurt on Emerald? |
| Longer memory | main sweep `--rounds 1 13 4` | 8 × 2000 | 8–9 | Fit quality and drift at higher r |

Always run `--preflight` (free) first, and `scripts/fetch_calibration.py` after IQM recalibrates.

## After each run (free)

```bash
python scripts/diagnose_hardware_rounds.py results/<sweep>/<ts> --output results/<sweep>/<ts>/diagnosis
python scripts/redecode_sweep.py results/<sweep>/<ts> --decoder pymatching_pij      # Google's p_ij decoder
python scripts/archive_baseline.py results/<sweep>/<ts> --output-root baselines/post_hackathon \
    --name <name> --provenance post_hackathon --title "<title>"
python scripts/fit_noise_to_hardware.py export-targets --config configs/hw_d3_noreset_dd_sim.yaml \
    --run results/<sweep>/<ts>/runs/<..._rounds_1>/<ts> --output baselines/post_hackathon/<name>/targets_r1.json
```

- `pymatching_pij` re-estimates every matching-graph edge probability from the hardware detection events, cross-fitted on odd/even shots (Google, Nature 595 and 614). It is usually the best decoder for real data.
- Report the error per round from the summary's per-round fit (binomial maximum likelihood with free amplitude), with its 1σ.

## Known limits

- The noise model is still approximate: no leakage, crosstalk, or measurement-induced dephasing.
- The two-qubit scale (1.5) was fitted to June r=1 data. A refit on the October r=1 data (2q 1.5, readout ×3) over-predicted higher rounds and was not adopted.
- A d=5 patch needs routing on Emerald and is above threshold in simulation, so it is not worth credits yet.
