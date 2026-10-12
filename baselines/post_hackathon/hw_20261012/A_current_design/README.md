# A: current design on IQM Emerald, rounds 1-13 (2026-10-12)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-12 07:22:42Z
- Source sweep: `results\hw_d3_noreset_dd_iqm__shots=1000_rounds_sweep\20261012T071921_905006Z`
- Code that produced the sweep: `7a97d95`
- Notes: No mid-circuit reset, grouped readout, IQM DD, passive reset between shots; 1000 shots per point.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.041 | 0.03517–0.04774 | 1000/1000 | 0.102375 |  |
| 1 | memory_z | 0.061 | 0.05386–0.06902 | 1000/1000 | 0.096375 |  |
| 3 | memory_x | 0.123 | 0.113–0.1338 | 1000/1000 | 0.12825 |  |
| 3 | memory_z | 0.141 | 0.1304–0.1524 | 1000/1000 | 0.129958 |  |
| 5 | memory_x | 0.153 | 0.142–0.1647 | 1000/1000 | 0.139325 |  |
| 5 | memory_z | 0.203 | 0.1906–0.216 | 1000/1000 | 0.139725 |  |
| 7 | memory_x | 0.215 | 0.2023–0.2283 | 1000/1000 | 0.147607 |  |
| 7 | memory_z | 0.278 | 0.2641–0.2924 | 1000/1000 | 0.144625 |  |
| 9 | memory_x | 0.234 | 0.2209–0.2476 | 1000/1000 | 0.151778 |  |
| 9 | memory_z | 0.308 | 0.2936–0.3228 | 1000/1000 | 0.154569 |  |
| 11 | memory_x | 0.319 | 0.3044–0.3339 | 1000/1000 | 0.159 |  |
| 11 | memory_z | 0.334 | 0.3193–0.3491 | 1000/1000 | 0.159614 |  |
| 13 | memory_x | 0.331 | 0.3163–0.346 | 1000/1000 | 0.165279 |  |
| 13 | memory_z | 0.376 | 0.3608–0.3914 | 1000/1000 | 0.168471 |  |

## Hardware Metadata

- Jobs: 01a12efb-138e-7697-98ca-1fd3a05bb42e (submitted 2026-10-12T07:19:28+00:00 UTC)
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 117
- Max transpiled two-qubit gates: 312
- Max SWAP count: 0
- Dynamical decoupling requested: True
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
