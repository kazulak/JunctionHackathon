# Rounds Sweep: redecode_pymatching

- Code: `7a97d95` on `oct12-run`, recorded 2026-10-12T07:22:49+00:00
- Config: `results\hw_d3_noreset_dd_iqm__shots=1000_rounds_sweep\20261012T071921_905006Z`
- Rounds: [1, 3, 5, 7, 9, 11, 13]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.041 | 0.03517–0.04774 | 0.041 | 0.1024 | 1000/1000 | 41 | 1000 | fixed / out-of-sample |
| 1 | memory_z | 0.061 | 0.05386–0.06902 | 0.061 | 0.09638 | 1000/1000 | 61 | 1000 | fixed / out-of-sample |
| 11 | memory_x | 0.276 | 0.2621–0.2904 | 0.0352 | 0.159 | 1000/1000 | 276 | 1000 | fixed / out-of-sample |
| 11 | memory_z | 0.312 | 0.2975–0.3268 | 0.04254 | 0.1596 | 1000/1000 | 312 | 1000 | fixed / out-of-sample |
| 13 | memory_x | 0.304 | 0.2897–0.3187 | 0.03475 | 0.1653 | 1000/1000 | 304 | 1000 | fixed / out-of-sample |
| 13 | memory_z | 0.331 | 0.3163–0.346 | 0.04003 | 0.1685 | 1000/1000 | 331 | 1000 | fixed / out-of-sample |
| 3 | memory_x | 0.119 | 0.1091–0.1296 | 0.04331 | 0.1283 | 1000/1000 | 119 | 1000 | fixed / out-of-sample |
| 3 | memory_z | 0.138 | 0.1275–0.1493 | 0.05103 | 0.13 | 1000/1000 | 138 | 1000 | fixed / out-of-sample |
| 5 | memory_x | 0.144 | 0.1333–0.1555 | 0.03284 | 0.1393 | 1000/1000 | 144 | 1000 | fixed / out-of-sample |
| 5 | memory_z | 0.185 | 0.173–0.1976 | 0.04413 | 0.1397 | 1000/1000 | 185 | 1000 | fixed / out-of-sample |
| 7 | memory_x | 0.197 | 0.1847–0.2099 | 0.03453 | 0.1476 | 1000/1000 | 197 | 1000 | fixed / out-of-sample |
| 7 | memory_z | 0.233 | 0.2199–0.2466 | 0.04286 | 0.1446 | 1000/1000 | 233 | 1000 | fixed / out-of-sample |
| 9 | memory_x | 0.237 | 0.2238–0.2507 | 0.03445 | 0.1518 | 1000/1000 | 237 | 1000 | fixed / out-of-sample |
| 9 | memory_z | 0.277 | 0.2631–0.2914 | 0.0429 | 0.1546 | 1000/1000 | 277 | 1000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 7 | 0.03374 | 0.001658 | 0.978 |
| memory_z | 7 | 0.03973 | 0.002014 | 0.948 |
