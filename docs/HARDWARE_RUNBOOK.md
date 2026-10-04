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
4. Uses active reset between shots (`active_reset_cycles: 2`): ~0.01–0.02 ms of schedule per shot instead of ~0.41 ms.
5. Uses today's calibration (`scripts/fetch_calibration.py`), per-shot memory, recorded physical qubits, and a layout guard.

## Before spending credits (all free)

```bash
python scripts/fetch_calibration.py                              # current calibration -> configs/calibration/
python scripts/sweep_rounds.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 2 --preflight
python scripts/pulla_schedule_report.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 5 7 9 \
    --active-reset-cycles 2 --dd --shots 4000                    # schedule length per shot
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

## Credit plan (30 credits)

The schedule cost is tiny, but each job also carries fixed overhead. The June jobs ran 1.4–4.2 s beyond their schedule; the real per-job cost is unknown until the first job. So run in this order and check the cost in the Resonance dashboard (Jobs) after each step.

| Step | Command | Circuits × shots | Estimated credits | Go / no-go |
| --- | --- | --- | ---: | --- |
| 1. Pilot | `sweep_rounds.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 2` | 4 × 2000 | 1–5 | r=3 memory_z LER < 0.2 means the fix works; ≈0.5 means go to step 4 |
| 2. Main sweep | `sweep_rounds.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 9 5` (set `shots: 4000`) | 10 × 4000 | 3–8 | Compare with the prediction |
| 3. Controls | same with `dynamical_decoupling: false`, and `mid_circuit_reset: reset`, r = 1, 3 | 8 × 2000 | 2–5 | Quantifies DD and reset strategy on hardware |
| 4. Only if step 1 fails | `sweep_rounds.py configs/probe_midcircuit_{measure_reset,measure,none}_iqm.yaml --rounds 1 3 2` | 4 × 2000 each | 1–5 each | See the hypothesis table in `baselines/post_hackathon/midcircuit_diagnosis_20261004` |

Keep ~10 credits in reserve.

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
- The two-qubit scale (1.5) was fitted to June r=1 data. Refit it on the pilot's r=1 data.
- A d=5 patch needs routing on Emerald and is above threshold in simulation, so it is not worth credits yet.
