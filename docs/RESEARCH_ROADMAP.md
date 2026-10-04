# Research Roadmap

## Priority 1: mid-circuit operations on hardware

Hardware data is destroyed from the first mid-circuit measure/reset (ERRATA E5). Nothing else matters for hardware LER until this is understood.

1. Run the probe experiment (needs IQM credits): `configs/probe_midcircuit_{measure_reset,measure,none}_iqm.yaml`, r = 1/3/5/7, plus `configs/sweep_d3_no_reset_iqm.yaml`.
2. Compare the per-data-qubit flip rate with the simulator reference (`baselines/post_hackathon/midcircuit_probe_sim_reference_20261004`).
3. Read the outcome against the hypothesis table in `baselines/post_hackathon/midcircuit_diagnosis_20261004/README.md`.
4. Ask IQM which `reset` implementation and mid-circuit readout timing Emerald uses.

Keep the workflow simulator-first. Spend QPU credits only after local sweeps show a clear reason.

## Ideas From Google's Surface-Code Paper

Reference: Google Quantum AI, "Quantum error correction below the surface code threshold",
[arXiv:2408.13687](https://arxiv.org/abs/2408.13687) (Nature 638, 920–926, 2025).

1. Track detector firing probability, not only LER.
   - Use mean detector firing rate as a proxy for physical error.
   - If detector rates saturate, improve circuit/noise assumptions before blaming the decoder.

2. Fit logical error per round.
   - For a memory experiment, use:

```text
p_L(t) = 1/2 * (1 - (1 - 2e)^t)
```

   - `e` is the fitted logical error per round.
   - Compare improvements using both total LER and fitted per-round LER.

3. Build error-budget sweeps.
   - Scale one noise source at a time:

```text
CZ / two-qubit
measurement
reset
idle
one-qubit
correlated two-qubit or burst errors
```

   - Plot which source controls LER most strongly.

4. Improve decoder priors before jumping to GNN.
   - Start with calibrated MWPM weights and short calibration splits.
   - Then try BP/OSD, Union-Find, or GNN if MWPM stops improving.

5. Add correlated and time-correlated noise.
   - Local Pauli noise is not enough for real superconducting hardware.
   - First simulator extensions should model detector hot spots, readout bursts, leakage-like persistence, and CZ-correlated events.

6. Treat ZXXZ/code-family changes as second phase.
   - Do this after diagnostics, per-round fitting, and error-budget sweeps are stable.

## Current Low-Cost Improvements Under Test

Low-syndrome postselection, gated decoding, correlation-aware MWPM, and MWPM ensembles.

Postselection does not claim full QEC improvement because it discards shots. It is useful because it answers:

```text
Does the low-syndrome subset still contain correctable logical signal?
```

Gated decoding keeps all shots. It tries no correction on low-syndrome shots and MWPM on the rest. This tests whether MWPM is over-correcting very clean syndrome records.

Correlation-aware MWPM and ensemble decoding also keep all shots. These test whether the detector error model contains useful correlated-error information or whether several MWPM priors make different useful mistakes.

Current conclusion (corrected simulator, 2026-10-04, `baselines/post_hackathon/decoder_validation_idlefix_20261004`):

```text
same-batch candidate tuning: optimistic by construction, diagnostic only
k-fold selection: memory_x 0.035 -> 0.030 per round (correlated matching); memory_z unchanged
```

The June conclusion ("k-fold does not beat baseline") was drawn on the buggy noise model (ERRATA E1).
Decoder work does not matter on hardware until mid-circuit operations stop destroying the data (ERRATA E5).

Run:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_baseline_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_postselected_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_gated_decoder_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_decoder_improvements_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_decoder_kfold_sim.yaml --rounds 1 7 4
python scripts/compare_sweeps.py baseline=<baseline_sweep_dir> postselected=<postselected_sweep_dir> gated=<gated_sweep_dir> decoder_improved=<decoder_improved_sweep_dir> decoder_kfold=<decoder_kfold_sweep_dir>
```

Next improvement after this:

```text
noise-source scale sweep -> identify dominant simulator error source -> adjust model/decoder weights -> rerun comparison
```
