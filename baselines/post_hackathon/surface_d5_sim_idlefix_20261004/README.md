# d5 calibrated simulator (routed layout) after idle-noise fix (2026-10-04)
n> Superseded by `surface_d5_sim_fitted_noise_20261004` (noise model fitted to hardware). Kept to show the effect of the idle-noise fix alone.

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 10:58:09Z
- Source sweep: `results\sim_iqm_emerald_surface_d5_calibrated_rounds_sweep\20261004T105727_693356Z`
- Code that produced the sweep: `b2da57c`
- Notes: Same config as baselines/hackathon_2026-06-07/surface_d5_routed_sim, re-run after the ERRATA E1 fix. Plain calibrated MWPM decoder.

## Results

| Rounds | Basis | LER | Uncertainty | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.047 | 0.00669261 | 1000/1000 | 0.145542 |  |
| 3 | memory_z | 0.128 | 0.0105648 | 1000/1000 | 0.176306 |  |
| 5 | memory_z | 0.206 | 0.0127892 | 1000/1000 | 0.183633 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
