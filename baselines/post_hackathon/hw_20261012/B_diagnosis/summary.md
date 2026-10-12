# Round-by-round hardware diagnostics

Raw observable = logical observable from the final data measurement with no correction.
If it is ~0.5, the data qubits were scrambled before decoding.

| Sweep | Basis | Rounds | Shots | Raw observable flip | Decoded LER | X-ancilla P(1) by round | Z-ancilla P(1) by round | Detector rate by layer |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep | memory_x | 1 | 1000 | 0.219 | 0.040 | 0.05 | 0.49 | 0.05 0.12 |
| hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep | memory_x | 5 | 1000 | 0.434 | 0.206 | 0.06 0.13 0.17 0.22 0.24 | 0.49 0.19 0.48 0.27 0.47 | 0.06 0.16 0.16 0.17 0.18 0.14 |
| hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep | memory_x | 9 | 1000 | 0.467 | 0.297 | 0.07 0.15 0.19 0.24 0.26 0.28 0.32 0.33 0.35 | 0.51 0.19 0.49 0.27 0.48 0.32 0.48 0.37 0.48 | 0.07 0.17 0.17 0.18 0.18 0.18 0.18 0.18 0.19 0.15 |
| hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep | memory_z | 1 | 1000 | 0.108 | 0.047 | 0.49 | 0.05 | 0.05 0.12 |
| hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep | memory_z | 5 | 1000 | 0.400 | 0.270 | 0.49 0.14 0.47 0.24 0.46 | 0.05 0.17 0.20 0.25 0.26 | 0.05 0.16 0.17 0.18 0.16 0.14 |
| hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep | memory_z | 9 | 1000 | 0.475 | 0.383 | 0.50 0.15 0.49 0.23 0.48 0.30 0.47 0.35 0.47 | 0.05 0.18 0.20 0.27 0.27 0.33 0.32 0.37 0.36 | 0.05 0.16 0.17 0.17 0.18 0.19 0.18 0.20 0.19 0.17 |
