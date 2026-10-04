# Decoders and postselection on the final simulator (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Pipeline: all audit fixes. That means the idle-noise fix, k-fold decoder selection with the leak-free tie-break, Wilson intervals and the maximum-likelihood per-round fit, and the noise model fitted to r=1 hardware (`two_qubit_scale: 2.0`).
- d = 3, IQM Emerald pinned patch, 2000 shots per point
- Supersedes `decoder_validation_idlefix_20261004` (old hand-tuned scales) and all `*_20260608` simulator comparisons

| Label | Config | What it is |
| --- | --- | --- |
| `baseline` | `sweep_d3_baseline_sim.yaml` | plain calibrated MWPM |
| `in_sample_improved` | `sweep_d3_decoder_improvements_sim.yaml` | best of 83 decoder candidates on the same shots (optimistic) |
| `kfold` | `sweep_d3_decoder_kfold_sim.yaml` | same candidates, 5-fold out-of-fold selection |
| `postselect_q25` | `sweep_d3_low_syndrome_sim.yaml` | keeps shots at or below the 25% syndrome-weight quantile; k-fold decoder selection |

## Error per round (binomial MLE, ±1σ)

| | memory_z | memory_x |
| --- | ---: | ---: |
| baseline | 0.0680 ± 0.0020 | 0.0916 ± 0.0025 |
| kfold | 0.0643 ± 0.0019 | 0.0834 ± 0.0023 |
| in_sample_improved | 0.0629 ± 0.0018 | 0.0808 ± 0.0023 |

- **Out-of-sample decoder selection** lowers the error per round by about 5% (memory_z) and 9% (memory_x). The folds pick correlated matching.
- **In-sample selection** looks about 2–3% better again. That extra is selection bias.
- **Postselection** keeps 25–43% of shots (0/862 failures at r = 1, 68% upper bound 0.0012). It is excluded from the per-round fit because its kept fraction changes with r. Treat it as a diagnostic only.

These are simulator results. On hardware the data is lost at the first mid-circuit measure/reset (ERRATA E5), so none of this transfers until that is fixed.
