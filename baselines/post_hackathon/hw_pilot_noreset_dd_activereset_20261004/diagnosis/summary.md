# Round-by-round hardware diagnostics

Raw observable = logical observable from the final data measurement with no correction.
If it is ~0.5, the data qubits were scrambled before decoding.

| Sweep | Basis | Rounds | Shots | Raw observable flip | Decoded LER | X-ancilla P(1) by round | Z-ancilla P(1) by round | Detector rate by layer |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_x | 1 | 2000 | 0.355 | 0.309 | 0.35 | 0.52 | 0.35 0.35 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_x | 3 | 2000 | 0.428 | 0.385 | 0.36 0.41 0.43 | 0.52 0.39 0.51 | 0.36 0.40 0.36 0.36 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_z | 1 | 2000 | 0.339 | 0.290 | 0.52 | 0.33 | 0.33 0.33 |
| hw_d3_noreset_dd_iqm_rounds_sweep | memory_z | 3 | 2000 | 0.412 | 0.379 | 0.53 0.40 0.53 | 0.33 0.38 0.41 | 0.33 0.39 0.36 0.34 |
