# Rounds Sweep: sim_iqm_emerald_surface_d5_calibrated

- Code: `ea047b0` on `audit/5-noise-model`, recorded 2026-10-04T11:25:49+00:00
- Config: `configs\sim_iqm_emerald_surface_d5_calibrated.yaml`
- Rounds: [1, 3, 5]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.099 | 0.08995–0.1088 | 0.099 | 0.207 | 1000/1000 | 99 | 1000 | fixed / out-of-sample |
| 3 | memory_z | 0.325 | 0.3104–0.34 | 0.1476 | 0.2701 | 1000/1000 | 325 | 1000 | fixed / out-of-sample |
| 5 | memory_z | 0.452 | 0.4363–0.4678 | 0.1871 | 0.2818 | 1000/1000 | 452 | 1000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_z | 3 | 0.1405 | 0.005904 | 1 |
