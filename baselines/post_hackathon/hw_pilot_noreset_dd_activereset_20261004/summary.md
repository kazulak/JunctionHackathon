# Rounds Sweep: hw_d3_noreset_dd_iqm

- Code: `0bcdd12` on `main`, recorded 2026-10-04T12:52:57+00:00
- Config: `configs\hw_d3_noreset_dd_iqm.yaml`
- Rounds: [1, 3]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.29 | 0.28–0.3002 | 0.29 | 0.3309 | 2000/2000 | 580 | 2000 | fixed / out-of-sample |
| 1 | memory_x | 0.3095 | 0.2993–0.3199 | 0.3095 | 0.3516 | 2000/2000 | 619 | 2000 | fixed / out-of-sample |
| 3 | memory_z | 0.3785 | 0.3677–0.3894 | 0.188 | 0.362 | 2000/2000 | 757 | 2000 | fixed / out-of-sample |
| 3 | memory_x | 0.385 | 0.3742–0.3959 | 0.1937 | 0.3751 | 2000/2000 | 770 | 2000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 2 | 0.1115 | 0.02119 | 0.4904 |
| memory_z | 2 | 0.1197 | 0.0193 | 0.5522 |
