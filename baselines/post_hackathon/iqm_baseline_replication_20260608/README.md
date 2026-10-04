# IQM Emerald d3 baseline replication (2026-06-08)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 10:50:23Z
- Source sweep: `results\sweep_d3_best_iqm_rounds_sweep\20260608T203833Z`
- Notes: Post-hackathon re-run of the hack-era d3 IQM sweep (configs/sweep_d3_best_iqm.yaml). Reproduces the repeated-round saturation; previously not archived.

## Results

| Rounds | Basis | LER | Uncertainty | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.061 | 0.00535159 | 2000/2000 | 0.127688 | calibrated_or_configured |
| 1 | memory_z | 0.0585 | 0.00524775 | 2000/2000 | 0.153 | calibrated_or_configured |
| 3 | memory_x | 0.494 | 0.0111795 | 2000/2000 | 0.386813 | calibrated_or_configured |
| 3 | memory_z | 0.494 | 0.0111795 | 2000/2000 | 0.385 | uniform_p=0.1 |
| 5 | memory_x | 0.4785 | 0.01117 | 2000/2000 | 0.430525 | uniform_p=0.1 |
| 5 | memory_z | 0.497 | 0.0111801 | 2000/2000 | 0.429775 | uniform_p=0.2 |
| 7 | memory_x | 0.4935 | 0.0111794 | 2000/2000 | 0.451946 | uniform_p=0.05 |
| 7 | memory_z | 0.486 | 0.011176 | 2000/2000 | 0.451366 | uniform_p=0.02 |

## Hardware Metadata

- Jobs: 019ea8f5-df66-7b92-bf18-4080bea4abc3 (submitted 2026-06-08T20:39:06+00:00 UTC)
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 59
- Max transpiled two-qubit gates: 168
- Max SWAP count: 0
- Dynamical decoupling applied values: 

Detailed per-basis rows are in `hardware_metadata.csv`.

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `hardware_metadata.csv`
- `README.md`
