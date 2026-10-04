# Noise-model fit to IQM hardware (r=1), 2026-10-04

- Provenance: **Post-hackathon development (not part of the submission)**
- Purpose: replace the hand-tuned simulator scales (`qnd_scale: 0`, `idle_scale: 0.5`, chosen for *lowest* LER, ERRATA E2) with scales fitted to hardware.
- Script: `scripts/fit_noise_to_hardware.py`

## Data (`targets.json`)

Per-detector firing counts and raw logical-observable flips at **r = 1**, d = 3, IQM Emerald, pinned patch from `configs/sweep_d3_baseline_iqm.yaml`. Two post-hackathon hardware runs with identical circuits are pooled:

- job `019ea8f5-df66-7b92-bf18-4080bea4abc3` (2026-06-08 20:39 UTC)
- job `019ea8f7-5112-7b60-a001-7003aba9fb4d` (2026-06-08 20:40 UTC)

That is 4000 shots per basis, with 8 detectors plus 1 observable per basis. Only r = 1 is usable: from r = 2 onward mid-circuit measure/reset destroys the data (ERRATA E5).

## Model

Calibration-informed Pauli noise from the 2026-06-06 Emerald dump:

- RB infidelity converted to Pauli probabilities (×1.5 for one-qubit, ×1.25 for two-qubit gates);
- readout error = mean of the 0→1 and 1→0 assignment errors;
- idle error from Pauli-twirled T1/T2 with an assumed 1 µs round;
- no QND term in reset-based circuits.

## Fits (binomial deviance over 18 rates; lower is better)

| Grid | Best scales (two-qubit, readout, idle) | Deviance |
| --- | --- | ---: |
| coarse 5×5×5 | 2.0, 1.0, 0.5 | 710 |
| refined, idle free | 2.25, 1.25, 0.0 | 661 |
| refined, idle fixed at 1.0 (`fit_results.json`) | 2.0, 0.75, 1.0 | 732 |

Unscaled model (1, 1, 1): r=1 LER 0.024 (Z) / 0.034 (X) vs hardware 0.059 / 0.061.

## Decision

The two-qubit scale is ≈2 in every good fit, so **`two_qubit_scale: 2.0`** is adopted. Readout and idle are kept at their calibration values (scale 1.0), because at r = 1 they trade off against the two-qubit error and against each other: idle values from 0 to 1 and readout values from 0.75 to 1.25 differ by only a few percent in deviance. An idle scale of 0 is unphysical.

A two-qubit error about twice the isolated interleaved-RB value is plausible for a full surface-code round, where CZs run in parallel (crosstalk) and each CX also needs single-qubit rotations that the model does not include.

## Limits

- A deviance of ~700 for 18 rates is far from a good fit (≈15 would be expected). Uniform scales cannot reproduce the per-detector structure: hardware detector rates range from 0.05 to 0.25.
- Detectors are correlated, so the deviance is a pseudo-likelihood. Use it for ranking, not for confidence intervals.
- Nothing here constrains repeated-round effects.
