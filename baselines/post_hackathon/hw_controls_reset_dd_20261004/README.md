# IQM controls: active vs passive reset between shots, DD on/off (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- QPU: IQM Emerald (chip M216), calibration set `5cfaaf0e-735f-431d-97cd-815ba13ab9ce` (2026-10-04 05:09 UTC); the same set was used for patch selection and the noise model
- Circuit: d=3 rotated surface code, memory_z, r=1, `code.mid_circuit_reset: none`, grouped readout, pinned patch QB13–QB45
- Why: the pilot (`hw_pilot_noreset_dd_activereset_20261004`) failed already at r=1

| Job | Reset between shots | DD | LER | Z-ancilla P(1) (ideal ≈ 0) | Raw observable flip | QPU execution |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Pilot | active, 2 cycles | on | 0.290 | 0.330 | 0.339 | 1.24 s / 8000 shots |
| A | active, 2 cycles | off | 0.161 | 0.183 | 0.235 | 0.81 s / 1000 shots |
| B | passive (wait) | on | **0.027** | 0.045 | 0.122 | 1.01 s / 1000 shots |
| C | passive (wait) | off | **0.027** | 0.042 | 0.117 | 1.05 s / 1000 shots |

## Conclusions

1. **IQM's active reset between shots (`active_reset_cycles`) leaves qubits excited.** That means ~6–8% initialization error per qubit without DD and more with DD; the combination may place DD pulses inside the reset's feedback wait. The hardware config now uses passive reset.
2. **With passive reset, r=1 works and beats June** (LER 0.027 vs 0.049, with fresh calibration and grouped readout), close to the simulator prediction (0.015).
3. **DD has no effect at r=1**, as expected, because nothing idles long. Its expected benefit is at r ≥ 3, where data qubits idle during ancilla readout.
4. **Cost:** each job has ~0.6–0.8 s of fixed execution overhead, plus ~0.41 ms per shot with passive reset. Few, large jobs are cheaper than many small ones.
