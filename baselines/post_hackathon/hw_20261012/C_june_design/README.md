# C: June 2026 design on the same qubits (2026-10-12)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-12 07:22:44Z
- Source sweep: `results\hw_d3_noreset_dd_iqm__shots=500__mid_circuit_reset=reset__group_measurements=false__dynamical_decoupling=false__round_duration_s=7.65e-6__idle_t2=ramsey_rounds_sweep\20261012T072115_973008Z`
- Code that produced the sweep: `7a97d95`
- Notes: Qiskit reset after every ancilla measurement, ungrouped readout, no DD (the hackathon circuit); 500 shots per point.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.038 | 0.03033–0.04751 | 500/500 | 0.06825 |  |
| 1 | memory_z | 0.014 | 0.009632–0.02031 | 500/500 | 0.063 |  |
| 3 | memory_x | 0.472 | 0.4498–0.4944 | 500/500 | 0.339833 |  |
| 3 | memory_z | 0.446 | 0.4239–0.4683 | 500/500 | 0.314583 |  |
| 5 | memory_x | 0.494 | 0.4717–0.5163 | 500/500 | 0.3788 |  |
| 5 | memory_z | 0.514 | 0.4916–0.5363 | 500/500 | 0.3682 |  |

## Hardware Metadata

- Jobs: 01a12efc-c1dd-7015-8b73-960dffb5d51b (submitted 2026-10-12T07:21:19+00:00 UTC)
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 43
- Max transpiled two-qubit gates: 120
- Max SWAP count: 0
- Dynamical decoupling requested: False
- Active reset cycles between shots: none (passive reset)

Detailed per-basis rows are in `hardware_metadata.csv`.

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `hardware_metadata.csv`
- `README.md`
