# B: current design without dynamical decoupling (2026-10-12)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-12 07:22:43Z
- Source sweep: `results\hw_d3_noreset_dd_iqm__shots=1000__dynamical_decoupling=false__idle_t2=ramsey_rounds_sweep\20261012T072021_158704Z`
- Code that produced the sweep: `7a97d95`
- Notes: Same as A with DD off; 1000 shots per point.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.04 | 0.03425–0.04667 | 1000/1000 | 0.088125 |  |
| 1 | memory_z | 0.047 | 0.04075–0.05416 | 1000/1000 | 0.08325 |  |
| 5 | memory_x | 0.206 | 0.1935–0.2191 | 1000/1000 | 0.155875 |  |
| 5 | memory_z | 0.27 | 0.2562–0.2843 | 1000/1000 | 0.152 |  |
| 9 | memory_x | 0.297 | 0.2828–0.3116 | 1000/1000 | 0.171889 |  |
| 9 | memory_z | 0.383 | 0.3678–0.3985 | 1000/1000 | 0.172694 |  |

## Hardware Metadata

- Jobs: 01a12efb-eece-77aa-b352-1743a1ed5228 (submitted 2026-10-12T07:20:25+00:00 UTC)
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 81
- Max transpiled two-qubit gates: 216
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
