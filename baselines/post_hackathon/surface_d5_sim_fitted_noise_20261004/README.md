# d5 routed simulator with hardware-fitted noise model (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 11:26:09Z
- Source sweep: `results\sim_iqm_emerald_surface_d5_calibrated_rounds_sweep\20261004T112535_577975Z`
- Code that produced the sweep: `ea047b0`
- Notes: configs/sim_iqm_emerald_surface_d5_calibrated.yaml with the fitted noise model. Error per round ~0.14 vs ~0.068 for d3: on this routed Emerald layout d5 is above threshold.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.099 | 0.08995–0.1088 | 1000/1000 | 0.206958 |  |
| 3 | memory_z | 0.325 | 0.3104–0.34 | 1000/1000 | 0.270069 |  |
| 5 | memory_z | 0.452 | 0.4363–0.4678 | 1000/1000 | 0.281767 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
