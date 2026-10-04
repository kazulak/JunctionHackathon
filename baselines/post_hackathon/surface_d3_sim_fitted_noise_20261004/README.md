# d3 simulator with hardware-fitted noise model (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 11:26:07Z
- Source sweep: `results\sweep_d3_baseline_sim_rounds_sweep\20261004T112520_372665Z`
- Code that produced the sweep: `ea047b0`
- Notes: configs/sweep_d3_baseline_sim.yaml after audit phases 3-5: idle-noise fix, plain calibrated MWPM, physically converted noise with two_qubit_scale 2.0 fitted to r=1 hardware (noise_fit_targets_r1). This is the model's prediction for hardware IF mid-circuit operations worked (they currently do not, ERRATA E5).

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.0825 | 0.07655–0.08886 | 2000/2000 | 0.146625 |  |
| 1 | memory_z | 0.047 | 0.04249–0.05196 | 2000/2000 | 0.1385 |  |
| 3 | memory_x | 0.219 | 0.2099–0.2284 | 2000/2000 | 0.203146 |  |
| 3 | memory_z | 0.1795 | 0.1711–0.1882 | 2000/2000 | 0.197083 |  |
| 5 | memory_x | 0.3205 | 0.3102–0.331 | 2000/2000 | 0.213012 |  |
| 5 | memory_z | 0.2625 | 0.2528–0.2725 | 2000/2000 | 0.2098 |  |
| 7 | memory_x | 0.3995 | 0.3886–0.4105 | 2000/2000 | 0.217723 |  |
| 7 | memory_z | 0.339 | 0.3285–0.3497 | 2000/2000 | 0.216339 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
