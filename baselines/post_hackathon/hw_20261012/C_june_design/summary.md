# Rounds Sweep: hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey

- Code: `7a97d95` on `oct12-run`, recorded 2026-10-12T07:21:29+00:00
- Config: `configs\hw_d3_noreset_dd_iqm.yaml`
- Rounds: [1, 3, 5]
- Results: `sweep_results.csv`, `sweep_results.json`
- Plots: `ler_vs_rounds.png`, `detector_rate_vs_rounds.png`

## Results

LER interval: Wilson score interval (~68%). Per-round LER is blank for postselected rows.

| Rounds | Basis | LER | 68% interval | Per-round LER | Mean detector rate | Kept/original | Failures | Shots | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | memory_z | 0.014 | 0.009632–0.02031 | 0.014 | 0.063 | 500/500 | 7 | 500 | fixed / out-of-sample |
| 1 | memory_x | 0.038 | 0.03033–0.04751 | 0.038 | 0.06825 | 500/500 | 19 | 500 | fixed / out-of-sample |
| 3 | memory_z | 0.446 | 0.4239–0.4683 | 0.2619 | 0.3146 | 500/500 | 223 | 500 | fixed / out-of-sample |
| 3 | memory_x | 0.472 | 0.4498–0.4944 | 0.3087 | 0.3398 | 500/500 | 236 | 500 | fixed / out-of-sample |
| 5 | memory_z | 0.514 | 0.4916–0.5363 | 0.4909 | 0.3682 | 500/500 | 257 | 500 | fixed / out-of-sample |
| 5 | memory_x | 0.494 | 0.4717–0.5163 | 0.2936 | 0.3788 | 500/500 | 247 | 500 | fixed / out-of-sample |

## Per-round fit

Binomial maximum-likelihood fit of P(r) = (1 - A(1-2e)^r)/2; postselected rows excluded.

| Basis | Fit points | Error per round | 1-sigma | Amplitude A |
| --- | ---: | ---: | ---: | ---: |
| memory_x | 3 | 0.2729 | 0.004788 | 2 |
| memory_z | 3 | 0.2589 | 0.003192 | 2 |
