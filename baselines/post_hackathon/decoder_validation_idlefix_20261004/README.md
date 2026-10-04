# Decoder validation after the idle-noise fix (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Code: `audit/4-decoder-stats` (after the ERRATA E1 fix; k-fold default and tie-break fix from ERRATA E3)
- Simulator: d=3 rotated surface code, calibration-informed Emerald noise (hand-tuned scales, ERRATA E2), 2000 shots per point, seed 1
- Supersedes `decoder_improvements_20260608` and `decoder_validation_20260608`, which used the buggy noise model

| Label | Config | Decoder selection |
| --- | --- | --- |
| `baseline` | `configs/sweep_d3_baseline_sim.yaml` | plain calibrated MWPM (no selection) |
| `in_sample_improved` | `configs/sweep_d3_decoder_improvements_sim.yaml` | best of 83 candidates **on the same shots** (optimistic) |
| `kfold` | `configs/sweep_d3_decoder_kfold_sim.yaml` | same 83 candidates, 5-fold out-of-fold selection |
| `gated_kfold` | `configs/sweep_d3_gated_decoder_sim.yaml` | gated candidates, k-fold (new default) |

## Result

Fitted logical error per round (binomial MLE, ±1σ):

| | memory_z | memory_x |
| --- | ---: | ---: |
| baseline | 0.0279 ± 0.0010 | 0.0350 ± 0.0012 |
| kfold | 0.0275 ± 0.0010 | 0.0300 ± 0.0011 |
| in_sample_improved | 0.0269 ± 0.0010 | 0.0300 ± 0.0011 |

- **memory_x:** k-fold selection gives a real out-of-sample gain (≈14% lower error per round). The folds consistently choose correlated matching with a uniform prior (`correlated_uniform_p=0.001`).
- **memory_z:** no significant gain; the folds mostly choose correlated matching with calibrated priors.
- The fitted amplitude sits at its bound (A = 1) for all series, so the uncertainties are from the one-parameter curvature.

Open question: on data sampled from the calibrated model itself, correlated MWPM with *uniform* priors beats MWPM with the *true* calibrated priors for memory_x. That points to how the calibrated detector error model is decomposed or weighted, not to selection bias (the gain is out-of-sample). Worth checking before relying on the calibrated priors for hardware decoding.

Note: these statements differ from the June conclusion ("holdout/k-fold does not beat baseline"), which was drawn on the buggy noise model.
