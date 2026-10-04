# Pre-registered prediction for the d3 no-reset + DD hardware run (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 12:41:38Z
- Source sweep: `results\hw_d3_noreset_dd_sim_prediction_rounds_sweep\20261004T123646_271245Z`
- Code that produced the sweep: `bcb8af9` (uncommitted changes)
- Notes: Simulator twin (configs/hw_d3_noreset_dd_sim.yaml, 20k shots) of the planned IQM Emerald run, archived BEFORE any hardware data was taken. Calibration 2026-10-04T05:09Z (set 5cfaaf0e), two_qubit_scale 1.5 (refit on June r=1 data), round 1.29 us (Pulla), DD -> T2 echo. Predicted error per round: 0.0385 (memory_z), 0.0594 (memory_x).

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.02655 | 0.02544–0.02771 | 20000/20000 | 0.0935375 |  |
| 1 | memory_z | 0.0148 | 0.01397–0.01568 | 20000/20000 | 0.0715625 |  |
| 3 | memory_x | 0.127 | 0.1247–0.1294 | 20000/20000 | 0.1812 |  |
| 3 | memory_z | 0.0818 | 0.07988–0.08376 | 20000/20000 | 0.176358 |  |
| 5 | memory_x | 0.21405 | 0.2112–0.217 | 20000/20000 | 0.203247 |  |
| 5 | memory_z | 0.14775 | 0.1453–0.1503 | 20000/20000 | 0.200301 |  |
| 7 | memory_x | 0.2817 | 0.2785–0.2849 | 20000/20000 | 0.212183 |  |
| 7 | memory_z | 0.202 | 0.1992–0.2049 | 20000/20000 | 0.210182 |  |
| 9 | memory_x | 0.3287 | 0.3254–0.332 | 20000/20000 | 0.217416 |  |
| 9 | memory_z | 0.24625 | 0.2432–0.2493 | 20000/20000 | 0.215831 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
