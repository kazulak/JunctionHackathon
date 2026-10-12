# Rounds Sweep: hw_d3_noreset_dd_iqm__shots=1000

- Code: `7a97d95` on `oct12-run`, recorded 2026-10-12T07:20:06+00:00
- Config: `configs\hw_d3_noreset_dd_iqm.yaml`
- Rounds: [1, 3, 5, 7, 9, 11, 13]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.061 | 0.05386–0.06902 | 0.061 | 0.09638 | 1000/1000 | 61 | 1000 | fixed / out-of-sample |
| 1 | memory_x | 0.041 | 0.03517–0.04774 | 0.041 | 0.1024 | 1000/1000 | 41 | 1000 | fixed / out-of-sample |
| 3 | memory_z | 0.141 | 0.1304–0.1524 | 0.05227 | 0.13 | 1000/1000 | 141 | 1000 | fixed / out-of-sample |
| 3 | memory_x | 0.123 | 0.113–0.1338 | 0.04491 | 0.1283 | 1000/1000 | 123 | 1000 | fixed / out-of-sample |
| 5 | memory_z | 0.203 | 0.1906–0.216 | 0.04947 | 0.1397 | 1000/1000 | 203 | 1000 | fixed / out-of-sample |
| 5 | memory_x | 0.153 | 0.142–0.1647 | 0.03523 | 0.1393 | 1000/1000 | 153 | 1000 | fixed / out-of-sample |
| 7 | memory_z | 0.278 | 0.2641–0.2924 | 0.05476 | 0.1446 | 1000/1000 | 278 | 1000 | fixed / out-of-sample |
| 7 | memory_x | 0.215 | 0.2023–0.2283 | 0.03858 | 0.1476 | 1000/1000 | 215 | 1000 | fixed / out-of-sample |
| 9 | memory_z | 0.308 | 0.2936–0.3228 | 0.05044 | 0.1546 | 1000/1000 | 308 | 1000 | fixed / out-of-sample |
| 9 | memory_x | 0.234 | 0.2209–0.2476 | 0.03386 | 0.1518 | 1000/1000 | 234 | 1000 | fixed / out-of-sample |
| 11 | memory_z | 0.334 | 0.3193–0.3491 | 0.04769 | 0.1596 | 1000/1000 | 334 | 1000 | fixed / out-of-sample |
| 11 | memory_x | 0.319 | 0.3044–0.3339 | 0.04412 | 0.159 | 1000/1000 | 319 | 1000 | fixed / out-of-sample |
| 13 | memory_z | 0.376 | 0.3608–0.3914 | 0.05085 | 0.1685 | 1000/1000 | 376 | 1000 | fixed / out-of-sample |
| 13 | memory_x | 0.331 | 0.3163–0.346 | 0.04003 | 0.1653 | 1000/1000 | 331 | 1000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 7 | 0.03848 | 0.001757 | 0.9922 |
| memory_z | 7 | 0.04916 | 0.002265 | 0.9749 |
