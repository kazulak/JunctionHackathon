# Prediction B: current design without DD

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-12 07:06:10Z
- Source sweep: `results\hw_d3_noreset_dd_sim__shots=20000__idle_t2=ramsey_rounds_sweep\20261012T070526_502114Z`
- Code that produced the sweep: `c31598c` (uncommitted changes)
- Notes: idle_t2=ramsey. Pre-registered before the hardware run.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.083 | 0.08107–0.08497 | 20000/20000 | 0.151537 |  |
| 1 | memory_z | 0.02215 | 0.02113–0.02321 | 20000/20000 | 0.0793937 |  |
| 5 | memory_x | 0.3795 | 0.3761–0.3829 | 20000/20000 | 0.24653 |  |
| 5 | memory_z | 0.1704 | 0.1678–0.1731 | 20000/20000 | 0.233652 |  |
| 9 | memory_x | 0.46985 | 0.4663–0.4734 | 20000/20000 | 0.259391 |  |
| 9 | memory_z | 0.2762 | 0.273–0.2794 | 20000/20000 | 0.2524 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
