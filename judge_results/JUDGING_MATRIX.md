# Judging Matrix

| Criterion | What to show | Evidence |
| --- | --- | --- |
| Theoretical correctness, 40% | Stim-defined detectors/observables, PyMatching decoding, no-noise sanity, raw detector artifacts | `qec_pipeline/codes/`, `qec_pipeline/decoders/`, `docs/REPETITION_CODE_EXPLANATION.md`, run artifacts |
| Sophistication, 20% | Calibration-driven layouts, fixed Garnet patch, batch IQM submission, SWAP/depth accounting | `qec_pipeline/mapping/`, `qec_pipeline/backends/iqm_hardware.py`, `judge_results/tables/swap_depth_summary.csv` |
| LER statistics, 20% | Round sweeps, binomial uncertainty, shot counts, total and per-round LER | `judge_results/plots/`, `judge_results/tables/` |
| Flexibility and advanced functionality, 20% | YAML-swappable code/backend/decoder/noise modules, calibrated noise, postselection route, DD hook, future Ising/GNN/color-code slots | `configs/`, `docs/MODULE_INTEGRATION.md`, `docs/JUDGE_SUMMARY.md` |
| Bonus: hardware flexibility | Emerald and Garnet calibration files; configs can switch QPU/backend while preserving pipeline shape | `configs/2026-06-06T06_08_52.470451Z.json`, `configs/2026-06-06T16_44_10.718568Z.json` |
| Bonus: diagnosis | Identified repeated-round hardware saturation as the main blocker, separate from one-round correctness | `docs/JUDGE_SUMMARY.md`, `judge_results/README.md` |
