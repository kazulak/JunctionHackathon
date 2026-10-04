# Mid-circuit probe: simulator reference (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Configs: `configs/probe_midcircuit_{measure_reset,measure,none}_sim.yaml` (d = 3 qubits, pinned Emerald patch, hardware-fitted noise model), 2000 shots
- Purpose: the expected result for the hardware probe experiment described in `../midcircuit_diagnosis_20261004/README.md`

## How to read it

The probe is not a memory experiment.

- **"LER"** is the probability that **any** of the 9 idle data qubits flipped. It can exceed 0.5.
- **"Mean detector rate"** is the mean flip probability **per data qubit**, the number to compare with hardware.
- Per-round conversions and fits are intentionally left blank.

| Mean flip per data qubit | r=1 | r=3 | r=5 | r=7 |
| --- | ---: | ---: | ---: | ---: |
| memory_z, measure_reset | 0.023 | 0.035 | 0.058 | 0.073 |
| memory_x, measure_reset | 0.029 | 0.054 | 0.083 | 0.111 |
| memory_x, none | 0.027 | 0.057 | 0.084 | 0.109 |

All three modes agree within statistics. That is expected, because the simulator has no mechanism by which an ancilla measurement or reset disturbs the data. The remaining decay is readout plus idle (T1/T2) noise.

**On hardware**, if mid-circuit operations scramble the data as in the surface-code runs, the per-qubit flip will jump towards 0.5 from r = 1 to r = 3 in the affected modes. The pattern across the three modes then identifies the cause (see the hypothesis table in `../midcircuit_diagnosis_20261004/README.md`).
