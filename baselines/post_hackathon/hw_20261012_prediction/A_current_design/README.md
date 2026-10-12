# Prediction A: current design (no reset, grouped readout, DD), 2026-10-12 calibration

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-12 07:06:09Z
- Source sweep: `results\hw_d3_noreset_dd_sim__shots=20000_rounds_sweep\20261012T070517_891570Z`
- Code that produced the sweep: `c31598c` (uncommitted changes)
- Notes: Simulator twin, 20000 shots. Pre-registered before the hardware run.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.0376 | 0.03628–0.03897 | 20000/20000 | 0.107675 |  |
| 1 | memory_z | 0.02355 | 0.0225–0.02465 | 20000/20000 | 0.0793688 |  |
| 3 | memory_x | 0.15075 | 0.1482–0.1533 | 20000/20000 | 0.195054 |  |
| 3 | memory_z | 0.1015 | 0.09938–0.1037 | 20000/20000 | 0.186646 |  |
| 5 | memory_x | 0.24775 | 0.2447–0.2508 | 20000/20000 | 0.217073 |  |
| 5 | memory_z | 0.17105 | 0.1684–0.1737 | 20000/20000 | 0.21248 |  |
| 7 | memory_x | 0.3134 | 0.3101–0.3167 | 20000/20000 | 0.226607 |  |
| 7 | memory_z | 0.22865 | 0.2257–0.2316 | 20000/20000 | 0.223304 |  |
| 9 | memory_x | 0.3649 | 0.3615–0.3683 | 20000/20000 | 0.231911 |  |
| 9 | memory_z | 0.2771 | 0.2739–0.2803 | 20000/20000 | 0.229439 |  |
| 11 | memory_x | 0.39375 | 0.3903–0.3972 | 20000/20000 | 0.235355 |  |
| 11 | memory_z | 0.3146 | 0.3113–0.3179 | 20000/20000 | 0.233152 |  |
| 13 | memory_x | 0.421 | 0.4175–0.4245 | 20000/20000 | 0.237818 |  |
| 13 | memory_z | 0.34485 | 0.3415–0.3482 | 20000/20000 | 0.236025 |  |

## Files

- `sweep_results.csv`
- `sweep_results.json`
- `summary.md`
- `ler_vs_rounds.png`
- `detector_rate_vs_rounds.png`
- `README.md`
