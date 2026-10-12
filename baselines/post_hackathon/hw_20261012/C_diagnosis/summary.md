# Round-by-round hardware diagnostics

Raw observable = logical observable from the final data measurement with no correction.
If it is ~0.5, the data qubits were scrambled before decoding.

| Sweep | Basis | Rounds | Shots | Raw observable flip | Decoded LER | X-ancilla P(1) by round | Z-ancilla P(1) by round | Detector rate by layer |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep | memory_x | 1 | 500 | 0.090 | 0.038 | 0.07 | 0.50 | 0.07 0.07 |
| hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep | memory_x | 3 | 500 | 0.510 | 0.472 | 0.07 0.33 0.37 | 0.48 0.47 0.45 | 0.07 0.37 0.41 0.42 |
| hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep | memory_x | 5 | 500 | 0.498 | 0.494 | 0.06 0.33 0.38 0.50 0.45 | 0.50 0.49 0.46 0.46 0.45 | 0.06 0.38 0.38 0.45 0.44 0.42 |
| hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep | memory_z | 1 | 500 | 0.080 | 0.014 | 0.50 | 0.07 | 0.07 0.06 |
| hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep | memory_z | 3 | 500 | 0.490 | 0.446 | 0.46 0.48 0.45 | 0.06 0.40 0.43 | 0.06 0.38 0.41 0.25 |
| hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep | memory_z | 5 | 500 | 0.494 | 0.514 | 0.48 0.48 0.46 0.48 0.43 | 0.05 0.40 0.43 0.43 0.44 | 0.05 0.38 0.40 0.46 0.45 0.26 |
