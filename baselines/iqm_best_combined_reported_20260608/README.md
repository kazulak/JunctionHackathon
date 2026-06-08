# IQM Best Combined Reported LER 2026-06-08

- Archived: 2026-06-08 20:47:10Z
- Source sweep: `results\sweep_d3_best_combined_iqm_rounds_sweep\20260608T204021Z`
- Notes: Real hardware Emerald run using combined postselection and decoder-candidate recipe.

## Results

| Rounds | Basis | LER | Uncertainty | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0 | 0 | 970/2000 | 0.121625 | calibrated_or_configured |
| 1 | memory_z | 0 | 0 | 836/2000 | 0.152625 | calibrated_or_configured |
| 3 | memory_x | 0.467994 | 0.0188192 | 703/2000 | 0.392 | uniform_p=0.05\|no_correction_for_weight_le_7_q0.5 |
| 3 | memory_z | 0.501344 | 0.0183308 | 744/2000 | 0.386958 | no_correction |
| 5 | memory_x | 0.480716 | 0.0185429 | 726/2000 | 0.440125 | correlated_calibrated_or_configured |
| 5 | memory_z | 0.456942 | 0.0208832 | 569/2000 | 0.4298 | correlated_uniform_p=0.005\|no_correction_for_weight_le_13_q0.25 |
| 7 | memory_x | 0.432836 | 0.020177 | 603/2000 | 0.453107 | correlated_uniform_p=0.05\|no_correction_for_weight_le_22_q0.5 |
| 7 | memory_z | 0.43662 | 0.0196201 | 639/2000 | 0.451634 | correlated_uniform_p=0.003 |

## Hardware Metadata

- Jobs: 019ea8f7-5112-7b60-a001-7003aba9fb4d
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 59
- Max transpiled two-qubit gates: 168
- Max SWAP count: 0
- Dynamical decoupling applied values: False

Detailed per-basis rows are in `hardware_metadata.csv`.

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `hardware_metadata.csv`
- `README.md`
