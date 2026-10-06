# Baselines

Archived result summaries (`results/` is ignored). Split by provenance:

- [`hackathon_2026-06-07/`](hackathon_2026-06-07/): runs made **during Junction Quantum Hack 2026**, before the submission. The submission itself is frozen on tag `junction-quantum-hackathon-final-2026`.
- [`post_hackathon/`](post_hackathon/): everything run **after** the submission (2026-06-08 onward). Not part of the hackathon entry.

Timeline: [PROVENANCE.md](../PROVENANCE.md). Known issues: [ERRATA.md](../ERRATA.md).

## Hackathon runs (2026-06-07)

| Folder | Run (UTC) | Meaning |
| --- | --- | --- |
| `surface_d5_routed_sim/` | 00:39 | d5 simulator, routed Emerald layout. Includes the idle-noise bug (ERRATA E1). |
| `surface_d3_calibrated_sim/` | 01:15 | d3 simulator, r = 1/3/5/7. Includes the idle-noise bug. |
| `surface_d3_iqm_hardware/` | 01:15 (IQM job `019e9fa6…`) | d3 IQM Emerald hardware: saturates at LER ≈ 0.49 from r = 3 (ERRATA E5). |
| `surface_d3_postselected_sim/` | 01:25 | d3 simulator with postselection (keeps ~50–60 % of shots). |

## Post-hackathon runs

**Hardware, October 2026 (the current result)**

| Folder | Run (UTC) | Meaning |
| --- | --- | --- |
| `hw_d3_noreset_dd_prediction_20261004/` | 2026-10-04 12:36 | Simulator prediction, archived before any hardware run: 0.039 / 0.059 error per round. |
| `hw_pilot_noreset_dd_activereset_20261004/` | IQM job `01a106f9…`, 12:52 | Pilot: IQM active reset between shots leaves qubits excited (r = 1 LER 0.29). |
| `hw_controls_reset_dd_20261004/` | 13:00 | Three controls: passive reset fixes it (r = 1 LER 0.027); DD neutral at r = 1. |
| `hw_d3_noreset_dd_20261004/` | IQM job `01a10703…`, 13:03 | **Main result**: 0.033 (memory_z) / 0.040 (memory_x) error per round. Includes round diagnosis, p_ij re-decode and model comparison. |

**Hardware, June 2026 (diagnosing the failure)**

| Folder | Run (UTC) | Meaning |
| --- | --- | --- |
| `iqm_baseline_replication_20260608/` | IQM job `019ea8f5…`, 2026-06-08 20:39 | Re-run of the hackathon hardware sweep; reproduces the saturation. |
| `iqm_best_combined_reported_20260608/` | IQM job `019ea8f7…`, 2026-06-08 20:40 | Same with postselection; DD was requested but **not applied** (ERRATA E6). |
| `midcircuit_diagnosis_20261004/` | analysis 2026-10-04 | Round-by-round analysis of the two June runs: data qubits are scrambled once mid-circuit measure/reset begins. |

**Simulator (final pipeline, 2026-10-04)**

| Folder | Meaning |
| --- | --- |
| `noise_fit_targets_r1/` | r = 1 hardware detector counts and the fit of the two-qubit noise scale. |
| `surface_d3_sim_fitted_noise_20261004/` | d3 reference simulator (Qiskit-style reset each round, plain MWPM). |
| `surface_d5_sim_fitted_noise_20261004/` | Routed d5: above threshold on this layout. |
| `decoder_and_postselection_fitted_noise_20261004/` | Decoders: k-fold selection lowers error per round by ~5 % (Z) / ~9 % (X); postselection is a diagnostic. |

**Removed as superseded (2026-10-06).** June simulator comparisons made with the idle-noise bug, the intermediate
"idlefix" re-runs, the mid-circuit probe simulator reference, and an r = 1 refit that was not adopted. They remain in
git history: `git show f3c0b3d:baselines/post_hackathon/<folder>/README.md`. Archived summaries may name configs
that have since been removed; those are also in history at `f3c0b3d`.

## Archiving a new sweep

```bash
python scripts/archive_baseline.py results/<sweep>/<timestamp> \
    --output-root baselines/post_hackathon --name <folder> \
    --provenance post_hackathon --title "<title>"
```

The archive README records the provenance label, the git commit, and decoded IQM job submit times. Hardware folders also keep `hardware_metadata.csv` (job ID, calibration set, physical qubits, depth, gate counts).
