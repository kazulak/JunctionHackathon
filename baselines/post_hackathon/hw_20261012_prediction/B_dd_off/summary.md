# Rounds Sweep: hw_d3_noreset_dd_sim__shots=20000__idle_t2=ramsey

- Code: `c31598c` (uncommitted changes) on `oct12-run`, recorded 2026-10-12T07:05:28+00:00
- Config: `configs\hw_d3_noreset_dd_sim.yaml`
- Rounds: [1, 5, 9]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.02215 | 0.02113–0.02321 | 0.02215 | 0.07939 | 20000/20000 | 443 | 20000 | fixed / out-of-sample |
| 1 | memory_x | 0.083 | 0.08107–0.08497 | 0.083 | 0.1515 | 20000/20000 | 1660 | 20000 | fixed / out-of-sample |
| 5 | memory_z | 0.1704 | 0.1678–0.1731 | 0.03998 | 0.2337 | 20000/20000 | 3408 | 20000 | fixed / out-of-sample |
| 5 | memory_x | 0.3795 | 0.3761–0.3829 | 0.1238 | 0.2465 | 20000/20000 | 7590 | 20000 | fixed / out-of-sample |
| 9 | memory_z | 0.2762 | 0.273–0.2794 | 0.04272 | 0.2524 | 20000/20000 | 5524 | 20000 | fixed / out-of-sample |
| 9 | memory_x | 0.4698 | 0.4663–0.4734 | 0.134 | 0.2594 | 20000/20000 | 9397 | 20000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 3 | 0.1349 | 0.00233 | 1.142 |
| memory_z | 3 | 0.04486 | 0.0006283 | 1.05 |
