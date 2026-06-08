# Calibrated Simulation

Purpose:

```text
IQM calibration dump
-> select mapped qubits/couplers
-> inject per-qubit/per-coupler Stim noise
-> sample locally
-> decode detector events
-> compare LER vs rounds
```

Main command:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_sim.yaml --rounds 1 7 4
```

Postselection experiment:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_postselected_sim.yaml --rounds 1 7 4
```

D5 routed-layout experiment:

```bash
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d5_calibrated.yaml --rounds 1 5 3
```

Current useful knobs:

```yaml
noise:
  model: iqm_calibration
  options:
    apply_idle: true
    route_error_multiplier: 1.0
    qnd_scale: 0.0
    idle_scale: 0.5
```

Interpretation:

- Use simulator sweeps for rapid iteration.
- Only promote a config to IQM hardware after simulator LER improves.
- This model is still approximate; it does not fully capture pulse timing, leakage, crosstalk, drift, or repeated reset/readout history.
