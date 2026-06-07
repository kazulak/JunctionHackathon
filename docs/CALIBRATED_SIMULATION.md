# Calibrated Simulation

Purpose:

```text
real IQM calibration dump
-> mapping selects hardware qubits
-> noise.model: iqm_calibration injects qubit/coupler Stim noise
-> simulator samples the noisy circuit
-> pymatching_calibrated decodes the calibrated detector model
```

Run d3:

```bash
python main.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml --rounds 1 5 3
```

Run d5:

```bash
python main.py configs/sim_iqm_emerald_surface_d5_calibrated.yaml
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d5_calibrated.yaml --rounds 1 5 3
```

Current generated targets:

```text
d3 rotated, native mapped:
rounds 1: memory_z 0.0215, memory_x 0.0265
rounds 3: memory_z 0.183, memory_x 0.177
rounds 5: memory_z 0.3585, memory_x 0.389

d5 rotated, routed layout:
rounds 1: memory_z 0.047
rounds 3: memory_z 0.239
rounds 5: memory_z 0.409
```

Active model knobs:

```yaml
noise:
  options:
    qnd_scale: 0.0
    idle_scale: 0.5
```

Local search:

```bash
python scripts/search_calibrated_sim.py configs/sim_iqm_emerald_surface_d3_calibrated.yaml --basis memory_z --shots 1000 --top-patches 6
```

Latest search result:

```text
best variant: qnd_x0_idle_x0_5
memory_z LER: 0.024 +/- 0.00484
artifact: results/sim_iqm_emerald_surface_d3_calibrated_calibrated_search/20260607T003904Z
```

Main caveat: this is a Stim-level approximation. It does not simulate full Qiskit transpilation overhead, pulse timing, leakage, reset dynamics, crosstalk, or hardware queue drift.
