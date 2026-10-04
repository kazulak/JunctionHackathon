# d3 calibrated simulator after idle-noise fix (2026-10-04)

> Superseded by `surface_d3_sim_fitted_noise_20261004` (noise model fitted to hardware, plain MWPM). Kept to show the effect of the idle-noise fix alone.

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 10:58:09Z
- Source sweep: `results\sweep_d3_best_sim_rounds_sweep\20261004T105706_341713Z`
- Code that produced the sweep: `b2da57c`
- Notes: Same config as the hackathon run baselines/hackathon_2026-06-07/surface_d3_calibrated_sim, re-run after the ERRATA E1 fix. Decoder is still pymatching_auto with in-sample selection (ERRATA E3, fixed in phase 4).

## Results

| Rounds | Basis | LER | Uncertainty | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.0265 | 0.0035915 | 2000/2000 | 0.103438 | calibrated_or_configured |
| 1 | memory_z | 0.021 | 0.00320617 | 2000/2000 | 0.104125 | uniform_p=0.001 |
| 3 | memory_x | 0.094 | 0.00652549 | 2000/2000 | 0.135833 | uniform_p=0.001 |
| 3 | memory_z | 0.0805 | 0.00608357 | 2000/2000 | 0.135875 | calibrated_or_configured |
| 5 | memory_x | 0.153 | 0.00804957 | 2000/2000 | 0.143175 | uniform_p=0.001 |
| 5 | memory_z | 0.127 | 0.0074455 | 2000/2000 | 0.142738 | calibrated_or_configured |
| 7 | memory_x | 0.1975 | 0.00890207 | 2000/2000 | 0.147696 | uniform_p=0.001 |
| 7 | memory_z | 0.1685 | 0.00836982 | 2000/2000 | 0.14767 | calibrated_or_configured |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
