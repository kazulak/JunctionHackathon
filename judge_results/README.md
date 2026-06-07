# Judge Results

This folder is a curated subset of the full `results/` tree.

## Headline

- Surface-code pipeline is functional but saturates on hardware from round 3.
- Surface-code simulator degrades gradually, showing the hardware gap clearly.
- Repetition-code module is a final hardware-optimized path using only 5 qubits.
- Garnet repetition-code hardware reaches low total LER even at long rounds.

## Key Numbers

- Surface-code hardware artifact: `results/sweep_d3_best_iqm_rounds_sweep/20260607T011549Z`
- Surface-code simulator artifact: `results/sweep_d3_best_sim_rounds_sweep/20260607T011525Z`
- Repetition-code hardware artifact: `results/final_rep_code_iqm_rounds_sweep/20260607T062249Z`
- Repetition-code simulator artifact: `results/final_rep_code_sim_rounds_sweep/20260607T062152Z`

- Surface code r=3 hardware LER: 0.4870 +/- 0.0112
- Best repetition-code hardware LER: r=1 total 0.0026 +/- 0.0004
- Long repetition-code hardware LER: r=50 total 0.0163 +/- 0.0009
- Long repetition-code per-round LER: 0.000331 +/- 0.000018
- Literal transpiled `swap` gates: 0 in the curated hardware sweeps.
- Long repetition-code r=50 routing overhead: 219 transpiled two-qubit gates vs 200 logical two-qubit gates, so +19 two-qubit gates.

## Files

- `FINAL_ONE_PAGER.md`: shortest judge-facing project summary.
- `DEMO_SCRIPT.md`: two-minute presentation script.
- `JUDGING_MATRIX.md`: direct mapping to the challenge judging criteria.
- `plots/ler_vs_rounds_combined.png`: surface simulator/hardware vs repetition-code simulator/hardware.
- `plots/rep_code_per_round_ler.png`: per-round logical error for long memory runs.
- `tables/surface_code_simulator.csv`: surface-code simulator data.
- `tables/swap_depth_summary.csv`: SWAP/depth/two-qubit-gate evidence.
- `tables/repetition_code_hardware_per_round.csv`: total and per-round LER.

## Judging Criteria Mapping

- Theoretical correctness: Stim generates detectors/observables; PyMatching decodes detector events; artifacts include raw measurements and detector events.
- Sophistication: hardware-specific fixed layout, batch IQM submission, calibrated noise, explicit SWAP/depth summaries.
- LER statistics: all reported LER values include binomial uncertainties and shot counts.
- Flexibility: surface code, repetition code, simulator, IQM hardware, calibration-driven mapping/noise, postselection decoder route.

## Caveat

The repetition code protects one error channel, not full surface-code logical memory. We present it as a hardware-optimized QEC demonstration after identifying that full surface-code rounds saturate on current hardware.

The fitted simulator curve uses scaled Garnet calibration errors. The first-principles calibration-to-Stim model was too pessimistic for this shallow repetition-code run.

The fresh hardware curve is non-monotonic after round 26. We report it as measured and treat it as evidence of hardware/batch/reset dynamics, not as a monotonic threshold claim.
