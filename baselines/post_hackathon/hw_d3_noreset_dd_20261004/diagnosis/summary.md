# Round-by-round hardware diagnostics

Raw observable = logical observable from the final data measurement with no correction.
If it is ~0.5, the data qubits were scrambled before decoding.

| Sweep | Basis | Rounds | Shots | Raw observable flip | Decoded LER | X-ancilla P(1) by round | Z-ancilla P(1) by round | Detector rate by layer |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_x | 1 | 2000 | 0.279 | 0.040 | 0.06 | 0.50 | 0.06 0.14 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_x | 3 | 2000 | 0.393 | 0.112 | 0.06 0.14 0.18 | 0.49 0.18 0.48 | 0.06 0.16 0.17 0.15 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_x | 5 | 2000 | 0.439 | 0.163 | 0.06 0.14 0.18 0.22 0.25 | 0.49 0.18 0.48 0.26 0.48 | 0.06 0.16 0.17 0.16 0.17 0.15 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_x | 7 | 2000 | 0.456 | 0.229 | 0.06 0.14 0.17 0.22 0.25 0.28 0.30 | 0.50 0.18 0.49 0.27 0.48 0.32 0.47 | 0.06 0.16 0.17 0.17 0.18 0.18 0.19 0.17 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_z | 1 | 2000 | 0.128 | 0.035 | 0.49 | 0.05 | 0.05 0.17 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_z | 3 | 2000 | 0.239 | 0.089 | 0.49 0.15 0.48 | 0.05 0.17 0.20 | 0.05 0.16 0.16 0.19 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_z | 5 | 2000 | 0.327 | 0.154 | 0.50 0.15 0.49 0.24 0.48 | 0.05 0.16 0.21 0.25 0.28 | 0.05 0.16 0.17 0.17 0.17 0.18 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_z | 7 | 2000 | 0.370 | 0.189 | 0.50 0.15 0.49 0.24 0.47 0.30 0.47 | 0.05 0.17 0.21 0.26 0.28 0.31 0.32 | 0.05 0.16 0.17 0.17 0.17 0.18 0.18 0.19 |
