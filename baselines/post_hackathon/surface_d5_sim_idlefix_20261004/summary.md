# Rounds Sweep: sim_iqm_emerald_surface_d5_calibrated

- Code: `b2da57c` on `audit/3-idle-noise-fix`, recorded 2026-10-04T10:57:41+00:00
- Config: `configs\sim_iqm_emerald_surface_d5_calibrated.yaml`
- Rounds: [1, 3, 5]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

| Rounds | Basis | LER | Uncertainty | Per-round LER | Mean detector rate | Kept fraction | Failures | Shots |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | memory_z | 0.047 | 0.006692607862410586 | None | 0.14554166666666668 | 1.0 | 47 | 1000 |
| 3 | memory_z | 0.128 | 0.010564847372300274 | 0.0469345103916507 | 0.17630555555555555 | 1.0 | 128 | 1000 |
| 5 | memory_z | 0.206 | 0.0127892142057282 | 0.05038015708387994 | 0.18363333333333334 | 1.0 | 206 | 1000 |
