# Final Judge One-Pager

## Claim

We built a modular QEC experiment pipeline that can run the same YAML-defined job through Stim simulation or IQM hardware, decode detector events, and produce LER statistics with artifacts.

The full rotated surface-code path is functional, but repeated hardware rounds saturate near random LER. Our final low-depth improvement is a repetition-code route on Garnet, presented honestly as a one-channel QEC demonstration rather than full surface-code memory.

## Pipeline

```text
YAML config
-> code module: surface_code / surface_code_iqm / repetition_code
-> backend: Stim noisy simulator / IQM hardware
-> detector events from Stim detector model
-> decoder: PyMatching / calibrated MWPM / auto weight search
-> LER, uncertainty, raw measurements, syndrome data, plots
```

## Best Evidence

| Experiment | Rounds | LER | Evidence |
| --- | ---: | ---: | --- |
| Surface code on IQM hardware | 1 | 0.0490 +/- 0.0048 | surface path works before repeated-round saturation |
| Surface code on IQM hardware | 3 | 0.4870 +/- 0.0112 | identifies hardware repeated-round failure mode |
| Repetition code on IQM Garnet | 1 | 0.0026 +/- 0.0004 | best total LER |
| Repetition code on IQM Garnet | 50 | 0.0163 +/- 0.0009 | long memory run |
| Repetition code per-round LER | 50 | 0.000331 +/- 0.000018 | converted from total survival model |

## Hardware-Aware Work

- Real IQM calibration dumps drive patch selection and calibrated simulator noise.
- IQM sweeps use batch submission so all circuits are queued before waiting.
- Hardware metadata records depth, operation counts, job IDs, selected mapping, and SWAP/routing evidence.
- Curated runs show 0 literal transpiled `swap` gates; the long repetition-code run adds 19 two-qubit gates after routing.
- Experimental hooks exist for postselection, calibrated decoder weights, dynamical decoupling, and alternative code/decoder modules.

## What We Tried

- Distance-3 and distance-5 rotated surface-code memory.
- Memory-Z and memory-X basis runs.
- Emerald and Garnet calibration/hardware paths.
- Calibrated noisy Stim simulation from per-qubit and per-coupler data.
- Decoder weight sweeps and low-syndrome postselection.
- Final low-depth repetition-code module distilled from teammate code.

## What We Did Not Claim

- The repetition code is not full surface-code logical memory; it protects one error channel.
- NVIDIA Ising, GNN decoding, color code, and PulLA pulse compilation were evaluated as next routes, but not completed in the final runnable evidence path.
- The fitted simulator is useful for rapid iteration, but the first-principles Stim noise model still misses repeated reset/readout, leakage, crosstalk, and pulse-level effects.

## Artifacts

- Surface hardware: `results/sweep_d3_best_iqm_rounds_sweep/20260607T011549Z`
- Surface simulator: `results/sweep_d3_best_sim_rounds_sweep/20260607T011525Z`
- Repetition hardware: `results/final_rep_code_iqm_rounds_sweep/20260607T062249Z`
- Repetition simulator: `results/final_rep_code_sim_rounds_sweep/20260607T062152Z`
- Plots: `judge_results/plots/`
- Tables: `judge_results/tables/`
