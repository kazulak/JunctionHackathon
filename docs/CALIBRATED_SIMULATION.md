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
rounds 1: memory_z 0.168, memory_x 0.1705
rounds 3: memory_z 0.392, memory_x 0.397
rounds 5: memory_z 0.490, memory_x 0.474

d5 rotated, routed layout:
rounds 1: memory_z 0.307
rounds 3: memory_z 0.447
rounds 5: memory_z 0.501
```

Main caveat: this is a Stim-level approximation. It does not simulate full Qiskit transpilation overhead, pulse timing, leakage, reset dynamics, crosstalk, or hardware queue drift.
