# Rounds Sweep: hw_d3_noreset_dd_iqm

- Code: `0bcdd12` (uncommitted changes) on `pilot-findings`, recorded 2026-10-04T13:03:42+00:00
- Config: `configs\hw_d3_noreset_dd_iqm.yaml`
- Rounds: [1, 3, 5, 7]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.0355 | 0.03159–0.03988 | 0.0355 | 0.1099 | 2000/2000 | 71 | 2000 | fixed / out-of-sample |
| 1 | memory_x | 0.0395 | 0.03537–0.04409 | 0.0395 | 0.1031 | 2000/2000 | 79 | 2000 | fixed / out-of-sample |
| 3 | memory_z | 0.089 | 0.08284–0.09557 | 0.03162 | 0.1476 | 2000/2000 | 178 | 2000 | fixed / out-of-sample |
| 3 | memory_x | 0.1115 | 0.1047–0.1187 | 0.04033 | 0.1448 | 2000/2000 | 223 | 2000 | fixed / out-of-sample |
| 5 | memory_z | 0.154 | 0.1461–0.1622 | 0.03549 | 0.1568 | 2000/2000 | 308 | 2000 | fixed / out-of-sample |
| 5 | memory_x | 0.163 | 0.1549–0.1714 | 0.03794 | 0.1532 | 2000/2000 | 326 | 2000 | fixed / out-of-sample |
| 7 | memory_z | 0.1885 | 0.1799–0.1974 | 0.03268 | 0.1653 | 2000/2000 | 377 | 2000 | fixed / out-of-sample |
| 7 | memory_x | 0.229 | 0.2197–0.2385 | 0.04189 | 0.1662 | 2000/2000 | 458 | 2000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 4 | 0.04039 | 0.002039 | 1.003 |
| memory_z | 4 | 0.0331 | 0.001823 | 0.9964 |
