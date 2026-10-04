# Rounds Sweep: redecode_pymatching_pij

- Code: `0bcdd12` (uncommitted changes) on `pilot-findings`, recorded 2026-10-04T17:57:34+00:00
- Config: `results\hw_d3_noreset_dd_iqm_rounds_sweep\20261004T130313_769822Z`
- Rounds: [1, 3, 5, 7]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.043 | 0.03869–0.04777 | 0.043 | 0.1031 | 2000/2000 | 86 | 2000 | fixed / out-of-sample |
| 1 | memory_z | 0.0385 | 0.03442–0.04304 | 0.0385 | 0.1099 | 2000/2000 | 77 | 2000 | fixed / out-of-sample |
| 3 | memory_x | 0.1185 | 0.1115–0.1259 | 0.04311 | 0.1448 | 2000/2000 | 237 | 2000 | fixed / out-of-sample |
| 3 | memory_z | 0.092 | 0.08574–0.09867 | 0.03277 | 0.1476 | 2000/2000 | 184 | 2000 | fixed / out-of-sample |
| 5 | memory_x | 0.158 | 0.15–0.1663 | 0.03657 | 0.1532 | 2000/2000 | 316 | 2000 | fixed / out-of-sample |
| 5 | memory_z | 0.153 | 0.1451–0.1612 | 0.03523 | 0.1568 | 2000/2000 | 306 | 2000 | fixed / out-of-sample |
| 7 | memory_x | 0.2465 | 0.237–0.2563 | 0.04624 | 0.1662 | 2000/2000 | 493 | 2000 | fixed / out-of-sample |
| 7 | memory_z | 0.2285 | 0.2192–0.238 | 0.04177 | 0.1653 | 2000/2000 | 457 | 2000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 4 | 0.04199 | 0.002104 | 0.9994 |
| memory_z | 4 | 0.038 | 0.001903 | 1.005 |
