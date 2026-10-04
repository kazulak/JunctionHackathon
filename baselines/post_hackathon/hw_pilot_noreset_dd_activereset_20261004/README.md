# Pilot IQM run: no reset + DD + active reset (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 12:55:10Z
- Source sweep: `results\hw_d3_noreset_dd_iqm_rounds_sweep\20261004T125240_909340Z`
- Code that produced the sweep: `0bcdd12`
- Notes: First run of the corrected design (configs/hw_d3_noreset_dd_iqm.yaml, rounds 1 and 3). Execution 1.24 s for 8000 shots (0.155 ms/shot). UNEXPECTED: r=1 LER 0.29-0.31 (June r=1: 0.05). Deterministic first-round ancillas fire 0.33-0.35 in both bases: qubits start each shot with ~10-20% initialization error. Shot-to-shot carry-over is weak (+4-11 points), so this is not a simple missing reset. Suspects: IQM active reset between shots (active_reset_cycles: 2) and/or IQM native DD; the circuit and decoder at r=1 are otherwise identical to June.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.3095 | 0.2993–0.3199 | 2000/2000 | 0.351562 |  |
| 1 | memory_z | 0.29 | 0.28–0.3002 | 2000/2000 | 0.330875 |  |
| 3 | memory_x | 0.385 | 0.3742–0.3959 | 2000/2000 | 0.375125 |  |
| 3 | memory_z | 0.3785 | 0.3677–0.3894 | 2000/2000 | 0.362042 |  |

## Hardware Metadata

- Jobs: 01a106f9-5c87-70c2-acf7-c9ebbdbd83e1 (submitted 2026-10-04T12:52:47+00:00 UTC)
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 27
- Max transpiled two-qubit gates: 72
- Max SWAP count: 0
- Dynamical decoupling applied values: 

Detailed per-basis rows are in `hardware_metadata.csv`.

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `hardware_metadata.csv`
- `README.md`
