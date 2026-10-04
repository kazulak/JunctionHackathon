# IQM Emerald d3 memory with the corrected design (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Archived: 2026-10-04 18:00:54Z
- Source sweep: `results\hw_d3_noreset_dd_iqm_rounds_sweep\20261004T130313_769822Z`
- Code that produced the sweep: `0bcdd12` (uncommitted changes)
- Notes: configs/hw_d3_noreset_dd_iqm.yaml: no mid-circuit reset (two-round detectors), grouped readout, IQM native DD, passive reset between shots, Oct 4 calibration (set 5cfaaf0e, same set at run time). Error per round 0.033 +- 0.002 (memory_z), 0.040 +- 0.002 (memory_x); June hardware saturated at 0.49 from r=3. Execution 8.14 s for 16000 shots.

## Results

| Rounds | Basis | LER | 68% Wilson interval | Kept/Original | Detector rate | Candidate |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | memory_x | 0.0395 | 0.03537–0.04409 | 2000/2000 | 0.103125 |  |
| 1 | memory_z | 0.0355 | 0.03159–0.03988 | 2000/2000 | 0.109937 |  |
| 3 | memory_x | 0.1115 | 0.1047–0.1187 | 2000/2000 | 0.144792 |  |
| 3 | memory_z | 0.089 | 0.08284–0.09557 | 2000/2000 | 0.147583 |  |
| 5 | memory_x | 0.163 | 0.1549–0.1714 | 2000/2000 | 0.153213 |  |
| 5 | memory_z | 0.154 | 0.1461–0.1622 | 2000/2000 | 0.156762 |  |
| 7 | memory_x | 0.229 | 0.2197–0.2385 | 2000/2000 | 0.166187 |  |
| 7 | memory_z | 0.1885 | 0.1799–0.1974 | 2000/2000 | 0.165286 |  |

## Hardware Metadata

- Jobs: 01a10703-0fd1-7293-b12b-41e731d1126c (submitted 2026-10-04T13:03:23+00:00 UTC)
- QPU: M216_F0W102525_H03_F08
- Max transpiled depth: 63
- Max transpiled two-qubit gates: 168
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

## Findings

| Error per round (binomial MLE, ±1σ) | memory_z | memory_x |
| --- | ---: | ---: |
| **Hardware, calibrated MWPM** | **0.0331 ± 0.0018** | **0.0404 ± 0.0020** |
| Hardware, p_ij decoder (2-fold, 1000 training shots per fold) | 0.0380 ± 0.0019 | 0.0420 ± 0.0021 |
| Pre-registered simulator prediction | 0.0385 ± 0.0004 | 0.0594 ± 0.0006 |
| Simulator refit on this run's r=1 data only | 0.0443 ± 0.0006 | 0.0648 ± 0.0008 |

- June hardware saturated at LER ≈ 0.49 from r = 3. With the corrected design, r = 3 gives 0.089 (Z) / 0.112 (X), and logical information survives to r = 7 (0.19 / 0.23).
- **The pre-registered prediction held:** memory_z within ~15% at every r ≥ 3. memory_x is better on hardware than predicted, so the model overestimates dephasing with DD.
- **The r=1-only refit does not transfer.** It needs readout ×3 to match r = 1 and then over-predicts every later round. The r = 1 excess is a state-preparation / terminal-readout effect, not mid-circuit readout. The pre-registered model remains the reference.
- **p_ij is slightly worse here than the calibrated prior.** Pairwise correlations need far more shots (Google used 50k–100k); at 2000 shots per circuit, keep calibrated MWPM.
- **Detector rates stay at ~0.16–0.19 per layer** (first layer 0.05), with no saturation (`diagnosis/`).
- Files: `diagnosis/` (round-by-round), `redecoded_pij/`, `model_comparison/`.
