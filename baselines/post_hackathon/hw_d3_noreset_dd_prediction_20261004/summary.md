# Rounds Sweep: hw_d3_noreset_dd_sim_prediction

- Code: `bcb8af9` (uncommitted changes) on `hardware-readiness`, recorded 2026-10-04T12:41:37+00:00
- Config: `C:\Users\tomka\AppData\Local\Temp\claude\C--Users-tomka-repos-JunctionHackathon\ac1f4aa5-dd17-4503-9e53-768e64fcf681\scratchpad\hw\hw_sim_20k.yaml`
- Rounds: [1, 3, 5, 7, 9]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.0148 | 0.01397–0.01568 | 0.0148 | 0.07156 | 20000/20000 | 296 | 20000 | fixed / out-of-sample |
| 1 | memory_x | 0.02655 | 0.02544–0.02771 | 0.02655 | 0.09354 | 20000/20000 | 531 | 20000 | fixed / out-of-sample |
| 3 | memory_z | 0.0818 | 0.07988–0.08376 | 0.02891 | 0.1764 | 20000/20000 | 1636 | 20000 | fixed / out-of-sample |
| 3 | memory_x | 0.127 | 0.1247–0.1294 | 0.04653 | 0.1812 | 20000/20000 | 2540 | 20000 | fixed / out-of-sample |
| 5 | memory_z | 0.1477 | 0.1453–0.1503 | 0.03383 | 0.2003 | 20000/20000 | 2955 | 20000 | fixed / out-of-sample |
| 5 | memory_x | 0.214 | 0.2112–0.217 | 0.05287 | 0.2032 | 20000/20000 | 4281 | 20000 | fixed / out-of-sample |
| 7 | memory_z | 0.202 | 0.1992–0.2049 | 0.03563 | 0.2102 | 20000/20000 | 4040 | 20000 | fixed / out-of-sample |
| 7 | memory_x | 0.2817 | 0.2785–0.2849 | 0.05583 | 0.2122 | 20000/20000 | 5634 | 20000 | fixed / out-of-sample |
| 9 | memory_z | 0.2462 | 0.2432–0.2493 | 0.0363 | 0.2158 | 20000/20000 | 4925 | 20000 | fixed / out-of-sample |
| 9 | memory_x | 0.3287 | 0.3254–0.332 | 0.05611 | 0.2174 | 20000/20000 | 6574 | 20000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 5 | 0.05937 | 0.0006123 | 1.076 |
| memory_z | 5 | 0.03854 | 0.000429 | 1.052 |
