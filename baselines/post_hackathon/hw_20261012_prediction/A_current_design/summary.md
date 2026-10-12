# Rounds Sweep: hw_d3_noreset_dd_sim__shots=20000

- Code: `c31598c` (uncommitted changes) on `oct12-run`, recorded 2026-10-12T07:05:24+00:00
- Config: `configs\hw_d3_noreset_dd_sim.yaml`
- Rounds: [1, 3, 5, 7, 9, 11, 13]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.02355 | 0.0225–0.02465 | 0.02355 | 0.07937 | 20000/20000 | 471 | 20000 | fixed / out-of-sample |
| 1 | memory_x | 0.0376 | 0.03628–0.03897 | 0.0376 | 0.1077 | 20000/20000 | 752 | 20000 | fixed / out-of-sample |
| 3 | memory_z | 0.1015 | 0.09938–0.1037 | 0.03642 | 0.1866 | 20000/20000 | 2030 | 20000 | fixed / out-of-sample |
| 3 | memory_x | 0.1507 | 0.1482–0.1533 | 0.05637 | 0.1951 | 20000/20000 | 3015 | 20000 | fixed / out-of-sample |
| 5 | memory_z | 0.1711 | 0.1684–0.1737 | 0.04017 | 0.2125 | 20000/20000 | 3421 | 20000 | fixed / out-of-sample |
| 5 | memory_x | 0.2477 | 0.2447–0.2508 | 0.06394 | 0.2171 | 20000/20000 | 4955 | 20000 | fixed / out-of-sample |
| 7 | memory_z | 0.2286 | 0.2257–0.2316 | 0.04181 | 0.2233 | 20000/20000 | 4573 | 20000 | fixed / out-of-sample |
| 7 | memory_x | 0.3134 | 0.3101–0.3167 | 0.06567 | 0.2266 | 20000/20000 | 6268 | 20000 | fixed / out-of-sample |
| 9 | memory_z | 0.2771 | 0.2739–0.2803 | 0.04293 | 0.2294 | 20000/20000 | 5542 | 20000 | fixed / out-of-sample |
| 9 | memory_x | 0.3649 | 0.3615–0.3683 | 0.06766 | 0.2319 | 20000/20000 | 7298 | 20000 | fixed / out-of-sample |
| 11 | memory_z | 0.3146 | 0.3113–0.3179 | 0.04312 | 0.2332 | 20000/20000 | 6292 | 20000 | fixed / out-of-sample |
| 11 | memory_x | 0.3937 | 0.3903–0.3972 | 0.06567 | 0.2354 | 20000/20000 | 7875 | 20000 | fixed / out-of-sample |
| 13 | memory_z | 0.3448 | 0.3415–0.3482 | 0.04304 | 0.236 | 20000/20000 | 6897 | 20000 | fixed / out-of-sample |
| 13 | memory_x | 0.421 | 0.4175–0.4245 | 0.06616 | 0.2378 | 20000/20000 | 8420 | 20000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 7 | 0.06944 | 0.0006139 | 1.076 |
| memory_z | 7 | 0.04474 | 0.0003904 | 1.048 |
