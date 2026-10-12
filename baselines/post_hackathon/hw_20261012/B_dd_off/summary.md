# Rounds Sweep: hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey

- Code: `7a97d95` on `oct12-run`, recorded 2026-10-12T07:20:56+00:00
- Config: `configs\hw_d3_noreset_dd_iqm.yaml`
- Rounds: [1, 5, 9]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.047 | 0.04075–0.05416 | 0.047 | 0.08325 | 1000/1000 | 47 | 1000 | fixed / out-of-sample |
| 1 | memory_x | 0.04 | 0.03425–0.04667 | 0.04 | 0.08813 | 1000/1000 | 40 | 1000 | fixed / out-of-sample |
| 5 | memory_z | 0.27 | 0.2562–0.2843 | 0.07192 | 0.152 | 1000/1000 | 270 | 1000 | fixed / out-of-sample |
| 5 | memory_x | 0.206 | 0.1935–0.2191 | 0.05038 | 0.1559 | 1000/1000 | 206 | 1000 | fixed / out-of-sample |
| 9 | memory_z | 0.383 | 0.3678–0.3985 | 0.07452 | 0.1727 | 1000/1000 | 383 | 1000 | fixed / out-of-sample |
| 9 | memory_x | 0.297 | 0.2828–0.3116 | 0.04765 | 0.1719 | 1000/1000 | 297 | 1000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 3 | 0.05038 | 0.003323 | 1.022 |
| memory_z | 3 | 0.07789 | 0.004869 | 1.073 |
