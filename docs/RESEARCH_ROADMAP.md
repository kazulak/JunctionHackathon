# Research Roadmap

Keep the workflow simulator-first. Spend QPU credits only after local sweeps show a clear reason.

## Ideas From Google's Surface-Code Paper

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

## Current Low-Cost Improvement Under Test

Low-syndrome postselection.

This does not claim full QEC improvement because it discards shots. It is useful because it answers:

```text
Does the low-syndrome subset still contain correctable logical signal?
```

Run:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_postselected_sim.yaml --rounds 1 7 4
python scripts/compare_sweeps.py baseline=<baseline_sweep_dir> postselected=<postselected_sweep_dir>
```

Next improvement after this:

```text
noise-source scale sweep -> identify dominant simulator error source -> adjust model/decoder weights -> rerun comparison
```
