# Errata

Issues found in an audit in October 2026, after the hackathon. They affect numbers in the frozen submission (tags `hackathon-submission-2026-06-07` / `junction-quantum-hackathon-final-2026`) and in archived baselines.

The tags and the release are intentionally **not** changed. Corrections are made on `main` only; each entry says where it is fixed.

## E1. Calibrated simulator: idle noise grows with the square of the round count (critical)

`noise.model: iqm_calibration` spreads each qubit's per-round idle error over the TICKs of one round using `idle_tick_fraction = rounds / num_ticks`. `num_ticks` came from a helper that skips TICKs inside Stim `REPEAT` blocks, while idle noise is applied at every TICK of the flattened circuit. For r ≥ 3 each round therefore received r times its idle error, so total idle noise grew ~r² instead of ~r.

Effect, d=3 memory-Z, same config, 20 000 shots:

| | r=1 | r=3 | r=5 | r=7 |
| --- | ---: | ---: | ---: | ---: |
| Buggy: LER / error per round | 0.027 / 0.027 | 0.179 / 0.069 | 0.370 / 0.118 | 0.469 / 0.163 |
| Fixed: LER / error per round | 0.027 / 0.027 | 0.081 / 0.029 | 0.134 / 0.030 | 0.178 / 0.031 |

Consequences:

- The "simulator degrades gradually and saturates" curves in the submission and in `baselines/` are an artefact. With the fix the simulator is stationary (~3% per round).
- The real gap between hardware (≈0.49 at r=3) and the model is therefore much larger than reported, so the hardware failure is not "missing physics in the noise model" (see E5).
- Detector error models used to decode hardware data carried the same bug.

Status: **fixed on `main`** (audit phase 3, regression tests in `CalibratedNoiseScalingTests`). Corrected re-runs: `baselines/post_hackathon/surface_d3_sim_idlefix_20261004` (d3: error per round ≈0.028 memory-Z / ≈0.034 memory-X, constant in r) and `baselines/post_hackathon/surface_d5_sim_idlefix_20261004` (routed d5: ≈0.047–0.050 per round).

## E2. The "calibrated" simulator was hand-tuned towards low LER

The best simulator configs used `qnd_scale: 0.0` and `idle_scale: 0.5`. These were chosen by `scripts/search_calibrated_sim.py`, which keeps the variant with the **lowest** LER, not the variant that best matches hardware. With the unscaled calibration values, r=1 LER is 0.17, far above hardware (0.05–0.06), mainly because `1 − qndness` (which already includes readout error) was added as an extra readout flip.

Other approximations: randomized-benchmarking infidelity was used directly as the depolarizing probability (under-counts by 1.5× for one-qubit and 1.25× for two-qubit gates); readout error is the maximum of several fields; reset error is not available in the calibration dump and is always 0; the round time is assumed to be 1 µs.

The simulator should be described as *calibration-informed*, not *calibrated*.

Status: **fixed on `main`** (audit phase 5). The model now converts RB infidelity to Pauli probabilities, uses the mean readout assignment error, models idle noise as Pauli-twirled T1/T2, applies QND only to qubits reused without reset, and its scales are fitted to r=1 hardware data rather than chosen for low LER (`two_qubit_scale: 2.0`; see `baselines/post_hackathon/noise_fit_targets_r1` and `docs/CALIBRATED_SIMULATION.md`). The fit is still poor in absolute terms, so the model remains approximate.

## E3. Decoder candidate selection was in-sample

`pymatching_auto` defaulted to `candidate_selection_mode: current_batch`: it evaluates many decoder variants and reports the best one **on the same shots**. This is optimistic (winner's curse). Measured over 30 independent batches of 2000 shots with the 83-candidate configuration:

| | Apparent gain vs plain MWPM | Out-of-sample gain (k-fold) |
| --- | ---: | ---: |
| r=3 | −0.0058 ± 0.0008 | −0.0018 ± 0.0011 |
| r=5 | −0.0103 ± 0.0014 | −0.0016 ± 0.0019 (not significant) |

This affects the submission's surface-code tables (best of ~11 candidates), the repetition-code tables (best of 7), and the post-hackathon `decoder_improvements` / `best_combined` baselines. Holdout and k-fold also broke ties using the evaluation LER (a small test-set leak, ~0.0003).

Status: **fixed on `main`** (audit phase 4): `pymatching_auto` defaults to k-fold selection, in-sample selection is flagged `selection_is_in_sample`, ties are broken by candidate order, and the baseline configs use plain calibrated MWPM. On the corrected simulator, k-fold selection still gives a genuine gain for memory_x (0.035 → 0.030 per round; `baselines/post_hackathon/decoder_validation_idlefix_20261004`).

## E4. Repetition-code per-round LER on IQM Garnet is not supported by the data

The submission reports a d=3 repetition-code memory on Garnet with "per-round LER 0.000331 ± 0.000018" at r=50. The total LER is not monotonic in the number of rounds (0.033 at r=26, 0.0146 at r=42, 0.0163 at r=50), which a memory experiment cannot do, and hardware at r=1 (0.0026) beats the simulator (0.0096). A per-round error derived from such a curve is not meaningful.

A likely explanation (not verified on the Garnet data) is the same mid-circuit problem as E5: if mid-circuit records carry little information, the decoder relies mostly on the final readout and the LER stays roughly flat.

## E5. Surface-code hardware runs: data qubits are randomized by mid-circuit measure/reset

From the raw IQM Emerald data of the two post-hackathon sweeps (the hackathon sweep shows the same LER saturation; its raw data was not kept):

| | r=1 | r ≥ 3 |
| --- | ---: | ---: |
| Raw (uncorrected) logical flip, both bases | 0.12–0.14 | 0.48–0.52 |
| Z-type ancilla P(1) (should stay near 0 in memory-Z) | 0.14 | 0.40 in round 2, ~0.48 after |

r=1 circuits contain no mid-circuit operations; r ≥ 2 circuits contain mid-circuit measurements and `reset`s. Once those appear, the data qubits themselves are scrambled in both bases. No decoder, prior tuning, or postselection can recover this, so decoder-side "improvements" on these hardware runs are not meaningful. The submission's reading ("repeated reset/readout behaviour, timing, leakage, crosstalk") points in the right direction but understated how abrupt the failure is.

**Leading explanation (Oct 2026, from IQM's own compiler, no credits used).** Compiling the June circuits with IQM Pulla against the live Emerald calibration shows that each syndrome round took 7.6 µs instead of ~1.3 µs. Two things caused this. First, the converter emitted `measure, reset` per ancilla, which stops IQM from multiplexing the readouts. Second, every Qiskit `reset` is an extra measurement plus a feedback pulse. Meanwhile the data qubits idled without dynamical decoupling (Ramsey T2 ≈ 15 µs). The pipeline now groups readouts, encodes reset strategies faithfully (default for hardware: no reset, Gehér et al. arXiv:2408.00758), and enables IQM's native DD and active reset between shots. See `docs/HARDWARE_RUNBOOK.md`. The simulator predicts r = 3 LER ≈ 0.08 (memory_z) for the new configuration; a pilot hardware run will confirm or refute this.

Status: offline diagnostics done (audit phase 7). `scripts/diagnose_hardware_rounds.py` reproduces these numbers (`baselines/post_hackathon/midcircuit_diagnosis_20261004`). A characterization experiment is ready but **not yet run** on hardware (needs IQM credits): the `midcircuit_probe` code family (`configs/probe_midcircuit_{measure_reset,measure,none}_{sim,iqm}.yaml`) and `configs/sweep_d3_no_reset_iqm.yaml`. Simulator reference: `baselines/post_hackathon/midcircuit_probe_sim_reference_20261004`.

## E6. Statistics and reporting

- Postselected results were labelled by a target quantile ("postselect25") but kept 25–56% of shots, varying with r. They were reported as LER 0.000 ± 0 at r=1, and per-round fits were applied to them.
- Binomial standard errors are 0 when no failures are observed; a Wilson interval should be used.
- The per-round fit was an unweighted least-squares fit of log(1 − 2·LER) without an uncertainty.
- The IQM `dynamical_decoupling` option failed silently: the post-hackathon "combined" hardware run requested it, but it was never applied.

Status: postselection labelling, Wilson intervals, and the per-round fit (binomial maximum likelihood with uncertainty; postselected rows excluded) are **fixed on `main`** (audit phase 4). Dynamical decoupling: **fixed on `main`** (audit phase 6): requesting it on IQM now raises an error before any job is submitted. The hardware path also records per-shot memory (shot order), the IQM calibration-set ID, the calibration-file age, and the physical qubits actually sent to the QPU, and refuses to submit if a native patch would run on other qubits. Sweeps pin one qubit layout for all round values.
