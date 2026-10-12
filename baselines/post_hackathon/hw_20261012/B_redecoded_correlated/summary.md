# Rounds Sweep: redecode_pymatching

- Code: `7a97d95` on `oct12-run`, recorded 2026-10-12T07:22:51+00:00
- Config: `results\hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep\20261012T072021_158704Z`
- Rounds: [1, 5, 9]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.04 | 0.03425–0.04667 | 0.04 | 0.08813 | 1000/1000 | 40 | 1000 | fixed / out-of-sample |
| 1 | memory_z | 0.047 | 0.04075–0.05416 | 0.047 | 0.08325 | 1000/1000 | 47 | 1000 | fixed / out-of-sample |
| 5 | memory_x | 0.199 | 0.1867–0.2119 | 0.04826 | 0.1559 | 1000/1000 | 199 | 1000 | fixed / out-of-sample |
| 5 | memory_z | 0.268 | 0.2542–0.2822 | 0.07118 | 0.152 | 1000/1000 | 268 | 1000 | fixed / out-of-sample |
| 9 | memory_x | 0.295 | 0.2808–0.3096 | 0.04716 | 0.1719 | 1000/1000 | 295 | 1000 | fixed / out-of-sample |
| 9 | memory_z | 0.362 | 0.3469–0.3773 | 0.06664 | 0.1727 | 1000/1000 | 362 | 1000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 3 | 0.04896 | 0.003247 | 1.019 |
| memory_z | 3 | 0.07298 | 0.00462 | 1.06 |
