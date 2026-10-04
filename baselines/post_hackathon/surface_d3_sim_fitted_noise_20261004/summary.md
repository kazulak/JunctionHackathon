# Rounds Sweep: sweep_d3_baseline_sim

- Code: `ea047b0` on `audit/5-noise-model`, recorded 2026-10-04T11:25:32+00:00
- Config: `configs\sweep_d3_baseline_sim.yaml`
- Rounds: [1, 3, 5, 7]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.047 | 0.04249–0.05196 | 0.047 | 0.1385 | 2000/2000 | 94 | 2000 | fixed / out-of-sample |
| 1 | memory_x | 0.0825 | 0.07655–0.08886 | 0.0825 | 0.1466 | 2000/2000 | 165 | 2000 | fixed / out-of-sample |
| 3 | memory_z | 0.1795 | 0.1711–0.1882 | 0.06889 | 0.1971 | 2000/2000 | 359 | 2000 | fixed / out-of-sample |
| 3 | memory_x | 0.219 | 0.2099–0.2284 | 0.08738 | 0.2031 | 2000/2000 | 438 | 2000 | fixed / out-of-sample |
| 5 | memory_z | 0.2625 | 0.2528–0.2725 | 0.06917 | 0.2098 | 2000/2000 | 525 | 2000 | fixed / out-of-sample |
| 5 | memory_x | 0.3205 | 0.3102–0.331 | 0.09263 | 0.213 | 2000/2000 | 641 | 2000 | fixed / out-of-sample |
| 7 | memory_z | 0.339 | 0.3285–0.3497 | 0.07473 | 0.2163 | 2000/2000 | 678 | 2000 | fixed / out-of-sample |
| 7 | memory_x | 0.3995 | 0.3886–0.4105 | 0.1024 | 0.2177 | 2000/2000 | 799 | 2000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 4 | 0.09161 | 0.002544 | 1 |
| memory_z | 4 | 0.06797 | 0.001954 | 1 |
