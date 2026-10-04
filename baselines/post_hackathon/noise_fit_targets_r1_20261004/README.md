# Noise-model refit on 2026-10-04 hardware (r = 1)

- Provenance: **Post-hackathon development (not part of the submission)**
- Data: r = 1 runs of `baselines/post_hackathon/hw_d3_noreset_dd_20261004` (job `01a10703…`, 2000 shots per basis), calibration set `5cfaaf0e`
- Model: `configs/hw_d3_noreset_dd_sim.yaml`

Best grid point: `two_qubit_scale` 1.5 (unchanged from the June-data fit), `measurement_scale` 3.0 (deviance is flat between 2.5 and 4).

**Not adopted.** Validated against the unseen r = 3, 5, 7 hardware points, the refit over-predicts the logical error (ε 0.044 / 0.065 vs hardware 0.033 / 0.040). The pre-registered model (`measurement_scale` 1.0) predicts them better (0.039 / 0.059). The excess error at r = 1 belongs to state preparation or the terminal readout. A separate terminal-readout or initialization parameter would be the right refinement; a global readout scale is not.
