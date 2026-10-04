# Rounds Sweep: sweep_d3_best_sim

- Code: `b2da57c` on `audit/3-idle-noise-fix`, recorded 2026-10-04T10:57:24+00:00
- Config: `configs\sweep_d3_best_sim.yaml`
- Rounds: [1, 3, 5, 7]
- Results CSV: `sweep_results.csv`
- Results JSON: `sweep_results.json`
- Plot: `ler_vs_rounds.png`
- Detector-rate plot: `detector_rate_vs_rounds.png`

## Results

| Rounds | Basis | LER | Uncertainty | Per-round LER | Mean detector rate | Kept fraction | Failures | Shots |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | memory_z | 0.021 | 0.0032061659345704488 | None | 0.10412500000000001 | 1.0 | 42 | 2000 |
| 1 | memory_x | 0.0265 | 0.0035915003828483716 | None | 0.1034375 | 1.0 | 53 | 2000 |
| 3 | memory_z | 0.0805 | 0.006083574196144894 | 0.028417886385816826 | 0.135875 | 1.0 | 161 | 2000 |
| 3 | memory_x | 0.094 | 0.006525488487462069 | 0.03353183045071567 | 0.13583333333333333 | 1.0 | 188 | 2000 |
| 5 | memory_z | 0.127 | 0.007445501997850783 | 0.028460835303899534 | 0.14273750000000002 | 1.0 | 254 | 2000 |
| 5 | memory_x | 0.153 | 0.008049565205649308 | 0.03522592154991622 | 0.143175 | 1.0 | 306 | 2000 |
| 7 | memory_z | 0.1685 | 0.00836981929315084 | 0.028510596126451737 | 0.14766964285714285 | 1.0 | 337 | 2000 |
| 7 | memory_x | 0.1975 | 0.00890207138816579 | 0.034636624745872924 | 0.1476964285714286 | 1.0 | 395 | 2000 |
