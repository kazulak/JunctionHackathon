# Rounds Sweep: hw_d3_noreset_dd_sim__shots=20000__mid_circuit_reset=reset__round_duration_s=7.65e-6__idle_t2=ramsey

- Code: `c31598c` (uncommitted changes) on `oct12-run`, recorded 2026-10-12T07:05:32+00:00
- Config: `configs\hw_d3_noreset_dd_sim.yaml`
- Rounds: [1, 3, 5]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.12 | 0.1177–0.1223 | 0.12 | 0.1932 | 20000/20000 | 2399 | 20000 | fixed / out-of-sample |
| 1 | memory_x | 0.3528 | 0.3494–0.3561 | 0.3528 | 0.348 | 20000/20000 | 7055 | 20000 | fixed / out-of-sample |
| 3 | memory_z | 0.3308 | 0.3275–0.3341 | 0.1516 | 0.3147 | 20000/20000 | 6616 | 20000 | fixed / out-of-sample |
| 3 | memory_x | 0.4923 | 0.4887–0.4958 | 0.3753 | 0.3653 | 20000/20000 | 9845 | 20000 | fixed / out-of-sample |
| 5 | memory_z | 0.4289 | 0.4254–0.4324 | 0.1615 | 0.3385 | 20000/20000 | 8577 | 20000 | fixed / out-of-sample |
| 5 | memory_x | 0.4983 | 0.4948–0.5018 | 0.3396 | 0.369 | 20000/20000 | 9966 | 20000 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 3 | 0.3843 | 0.02601 | 1.272 |
| memory_z | 3 | 0.1684 | 0.002643 | 1.147 |
