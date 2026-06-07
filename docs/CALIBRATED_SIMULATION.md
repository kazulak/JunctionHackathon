# Calibrated Simulation

Purpose:

```text
IQM calibration dump
-> mapping selects the hardware patch
-> iqm_calibration injects per-qubit/per-coupler Stim noise
-> simulator samples noisy measurements
-> PyMatching decodes detector events
-> LER vs rounds plot
```

Current paired flow:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_best_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_best_iqm.yaml --rounds 1 7 4
```

Current postselected flow:

```bash
python scripts/sweep_rounds.py configs/sweep_d3_postselected_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sweep_d3_postselected_iqm.yaml --rounds 1 7 4
```

Active model knobs:

```yaml
noise:
  model: iqm_calibration
  options:
    apply_idle: true
    route_error_multiplier: 1.0
    qnd_scale: 0.0
    idle_scale: 0.5
```

Latest normal d3 simulator target, 2000 shots:

```text
artifact: results/sweep_d3_best_sim_rounds_sweep/20260607T011525Z
rounds 1: memory_z 0.021,  memory_x 0.0265
rounds 3: memory_z 0.1675, memory_x 0.2025
rounds 5: memory_z 0.367,  memory_x 0.358
rounds 7: memory_z 0.468,  memory_x 0.4715
```

Latest matching hardware d3 result, 2000 shots:

```text
artifact: results/sweep_d3_best_iqm_rounds_sweep/20260607T011549Z
rounds 1: memory_z 0.049, memory_x 0.0545
rounds 3: memory_z 0.487, memory_x 0.4925
rounds 5: memory_z 0.484, memory_x 0.4965
rounds 7: memory_z 0.472, memory_x 0.4825
```

Latest postselected d3 simulator result, keeping about half of shots:

```text
artifact: results/sweep_d3_postselected_sim_rounds_sweep/20260607T012558Z
rounds 1: memory_z 0.0,    memory_x 0.0
rounds 3: memory_z 0.0929, memory_x 0.1028
rounds 5: memory_z 0.3135, memory_x 0.3211
rounds 7: memory_z 0.4538, memory_x 0.4650
```

Read this as an experimental lever, not a solved decoder. It shows that low-syndrome shots still carry cleaner signal in the simulator. The next hardware check is whether `configs/sweep_d3_postselected_iqm.yaml` shows the same improvement.

Main caveat: this is a Stim-level approximation. It does not model full pulse timing, leakage, crosstalk, queue drift, or detailed repeated-reset dynamics.
