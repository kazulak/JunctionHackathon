# Round-by-round hardware diagnostics

Raw observable = logical observable from the final data measurement with no correction.
If it is ~0.5, the data qubits were scrambled before decoding.

| Sweep | Basis | Rounds | Shots | Raw observable flip | Decoded LER | X-ancilla P(1) by round | Z-ancilla P(1) by round | Detector rate by layer |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_x | 1 | 2000 | 0.121 | 0.000 | 0.11 | 0.50 | 0.11 0.13 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_x | 3 | 2000 | 0.494 | 0.468 | 0.10 0.41 0.43 | 0.47 0.46 0.49 | 0.10 0.44 0.47 0.42 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_x | 5 | 2000 | 0.517 | 0.481 | 0.11 0.40 0.45 0.49 0.47 | 0.48 0.47 0.49 0.47 0.49 | 0.11 0.44 0.48 0.51 0.50 0.42 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_x | 7 | 2000 | 0.477 | 0.433 | 0.11 0.39 0.44 0.50 0.48 0.48 0.45 | 0.47 0.46 0.48 0.47 0.48 0.47 0.49 | 0.11 0.44 0.47 0.50 0.50 0.49 0.51 0.42 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_z | 1 | 2000 | 0.129 | 0.000 | 0.50 | 0.15 | 0.15 0.15 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_z | 3 | 2000 | 0.505 | 0.501 | 0.49 0.47 0.46 | 0.14 0.41 0.49 | 0.14 0.42 0.48 0.38 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_z | 5 | 2000 | 0.501 | 0.457 | 0.49 0.49 0.48 0.49 0.47 | 0.15 0.39 0.49 0.48 0.48 | 0.15 0.40 0.47 0.50 0.50 0.40 |
| sweep_d3_best_combined_iqm_rounds_sweep | memory_z | 7 | 2000 | 0.491 | 0.437 | 0.49 0.48 0.48 0.49 0.50 0.49 0.46 | 0.15 0.42 0.49 0.48 0.48 0.48 0.48 | 0.15 0.42 0.47 0.50 0.50 0.50 0.49 0.40 |
| sweep_d3_best_iqm_rounds_sweep | memory_x | 1 | 2000 | 0.142 | 0.061 | 0.12 | 0.51 | 0.12 0.13 |
| sweep_d3_best_iqm_rounds_sweep | memory_x | 3 | 2000 | 0.502 | 0.494 | 0.11 0.39 0.43 | 0.47 0.46 0.49 | 0.11 0.43 0.47 0.41 |
| sweep_d3_best_iqm_rounds_sweep | memory_x | 5 | 2000 | 0.486 | 0.478 | 0.11 0.39 0.43 0.49 0.47 | 0.46 0.45 0.48 0.47 0.50 | 0.11 0.43 0.46 0.51 0.50 0.41 |
| sweep_d3_best_iqm_rounds_sweep | memory_x | 7 | 2000 | 0.510 | 0.493 | 0.11 0.39 0.43 0.50 0.48 0.48 0.47 | 0.48 0.46 0.48 0.47 0.49 0.47 0.49 | 0.11 0.44 0.47 0.51 0.50 0.50 0.49 0.41 |
| sweep_d3_best_iqm_rounds_sweep | memory_z | 1 | 2000 | 0.136 | 0.059 | 0.50 | 0.16 | 0.16 0.15 |
| sweep_d3_best_iqm_rounds_sweep | memory_z | 3 | 2000 | 0.507 | 0.494 | 0.49 0.48 0.47 | 0.14 0.40 0.48 | 0.14 0.41 0.48 0.39 |
| sweep_d3_best_iqm_rounds_sweep | memory_z | 5 | 2000 | 0.511 | 0.497 | 0.48 0.48 0.49 0.49 0.47 | 0.14 0.42 0.48 0.49 0.48 | 0.14 0.42 0.46 0.51 0.50 0.40 |
| sweep_d3_best_iqm_rounds_sweep | memory_z | 7 | 2000 | 0.492 | 0.486 | 0.49 0.48 0.48 0.48 0.49 0.49 0.47 | 0.15 0.41 0.48 0.48 0.49 0.49 0.49 | 0.15 0.41 0.46 0.51 0.51 0.49 0.49 0.42 |
