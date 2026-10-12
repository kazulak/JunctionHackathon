# IQM Emerald, 2026-10-12: reproduction, DD ablation, and the June design side by side

- Provenance: **Post-hackathon development (not part of the submission)**
- QPU: IQM Emerald (chip M216_F0W102525_H03_F08), calibration set `0174f8d8-543e-4a03-b208-77338e05df19` (2026-10-12 05:18 UTC); all three jobs ran within 2 minutes on the same set
- Circuit: d = 3 rotated surface-code memory, both bases, pinned patch QB13–QB45, passive reset between shots, calibrated MWPM decoder
- Predictions were archived and pushed before submission: [`../hw_20261012_prediction`](../hw_20261012_prediction/) (commit `7a97d95`)

| Job | Design | IQM job | QPU execution |
| --- | --- | --- | ---: |
| A | current: no mid-circuit reset, grouped readout, IQM DD; rounds 1–13, 1000 shots | `01a12efb-138e…` | 11.17 s |
| B | current design with DD **off**; rounds 1, 5, 9, 1000 shots | `01a12efb-eece…` | 2.83 s |
| C | June (hackathon) design: Qiskit reset after each ancilla readout, ungrouped readout, no DD; rounds 1, 3, 5, 500 shots | `01a12efc-c1dd…` | 2.07 s |

## Results

Logical error rate (LER) after r rounds:

| Rounds | A memory_z | A memory_x | B (no DD) memory_z | B (no DD) memory_x | C (June) memory_z | C (June) memory_x |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.061 | 0.041 | 0.047 | 0.040 | 0.014 | 0.038 |
| 3 | 0.141 | 0.123 | | | 0.446 | 0.472 |
| 5 | 0.203 | 0.153 | 0.270 | 0.206 | 0.514 | 0.494 |
| 7 | 0.278 | 0.215 | | | | |
| 9 | 0.308 | 0.234 | 0.383 | 0.297 | | |
| 11 | 0.334 | 0.319 | | | | |
| 13 | 0.376 | 0.331 | | | | |

Error per round (binomial maximum-likelihood fit, ±1σ):

| | memory_z | memory_x |
| --- | ---: | ---: |
| A, calibrated MWPM | 0.049 ± 0.002 | 0.038 ± 0.002 |
| A, correlated matching | 0.040 ± 0.002 | 0.034 ± 0.002 |
| B (no DD), calibrated MWPM | 0.078 ± 0.005 | 0.050 ± 0.003 |
| C (June design) | saturated (random from r = 3) | saturated |
| Prediction A | 0.045 | 0.069 |
| Prediction B (no DD) | 0.045 | 0.135 |
| 2026-10-04 main sweep (for reference) | 0.033 ± 0.002 | 0.040 ± 0.002 |

## Findings

1. **The fix is the circuit, shown on the same day and qubits.** From r = 3 the June design's uncorrected logical observable flips with probability 0.49–0.51 (`C_diagnosis/`) and decoding does not help (LER 0.45–0.51): the logical information is lost, as in June. The June circuit here is gate-for-gate the hackathon-tag circuit (same dependency graph, measurement order and qubits; checked against commit `16e86b1`). The current design keeps a working memory out to 13 rounds.
2. **The result reproduces.** memory_x is unchanged from 2026-10-04 (0.038 vs 0.040). memory_z is worse (0.049 vs 0.033); today's calibration has higher readout error on the patch (mean 1.5% vs 1.1%, QB13 3.0% vs 0.7%) and slightly higher CZ error (mean 0.51% vs 0.49%, worst coupler 2.0% vs 1.6%).
3. **DD matters, but not the way the model says.** Without DD the error per round rises by 58% (memory_z) and 31% (memory_x). The simulator attributes DD only to dephasing of idle data qubits, so it predicted no change for memory_z and a doubling for memory_x. The hardware shows the opposite emphasis. The model is missing an error source that DD suppresses (candidates: coherent ZZ crosstalk during readout, measurement-induced errors on neighbours).
4. **Correlated matching helps on hardware again** (−19% memory_z, −12% memory_x), consistent with 2026-10-04.

## Cost

16.07 s of QPU execution in total. Job A cost 0.80 ms per shot, versus 0.42 ms per shot predicted by IQM's pulse compiler and ~0.47 ms measured on 2026-10-04; jobs B and C cost at or below the estimate. Long, many-measurement circuits appear to carry extra per-shot overhead that the schedule length does not show.

## Folders

- `A_current_design/`, `B_dd_off/`, `C_june_design/`: sweep summaries and hardware metadata
- `*_diagnosis/`: round-by-round ancilla and detector rates, raw observable flip
- `*_redecoded_correlated/`: the same data decoded with correlated matching
- `comparison/`: hardware vs pre-registered predictions
