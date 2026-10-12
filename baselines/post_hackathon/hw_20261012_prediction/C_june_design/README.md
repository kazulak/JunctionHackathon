# Prediction C: June design (Qiskit reset, ungrouped readout, no DD)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-12 07:06:11Z
- Source sweep: `results\hw_d3_noreset_dd_sim__shots=20000__mid_circuit_reset=reset__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep\20261012T070530_708651Z`
- Code that produced the sweep: `c31598c` (uncommitted changes)
- Notes: round_duration_s=7.65e-6 (Pulla), idle_t2=ramsey. Uniform round duration overstates r=1 (the June r=1 circuit has no resets); qualitative only. Pre-registered before the hardware run.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.35275 | 0.3494–0.3561 | 20000/20000 | 0.348013 |  |
| 1 | memory_z | 0.11995 | 0.1177–0.1223 | 20000/20000 | 0.193219 |  |
| 3 | memory_x | 0.49225 | 0.4887–0.4958 | 20000/20000 | 0.365331 |  |
| 3 | memory_z | 0.3308 | 0.3275–0.3341 | 20000/20000 | 0.314742 |  |
| 5 | memory_x | 0.4983 | 0.4948–0.5018 | 20000/20000 | 0.368984 |  |
| 5 | memory_z | 0.42885 | 0.4254–0.4324 | 20000/20000 | 0.33845 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
