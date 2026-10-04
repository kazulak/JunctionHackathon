# Baselines

Compact result summaries. They are tracked in git because `results/` is ignored and disposable.

Results are split by provenance:

| Folder | What it contains |
| --- | --- |
| [`hackathon_2026-06-07/`](hackathon_2026-06-07/) | Runs made **during Junction Quantum Hack 2026**, before the submission (all on 2026-06-07 UTC). Archived on `main` after the event; the submission itself is frozen on tag `junction-quantum-hackathon-final-2026`. |
| [`post_hackathon/`](post_hackathon/) | Everything run **after** the submission (2026-06-08 onward). Not part of the hackathon entry. |

See [PROVENANCE.md](../PROVENANCE.md) for the full timeline and [ERRATA.md](../ERRATA.md) for known issues.

> **Known issue:** simulator results dated before 2026-10-04 were produced with the idle-noise scaling bug described in
> [ERRATA.md](../ERRATA.md) (idle noise grows ~r² with the number of rounds), so their LER for r ≥ 3 is too high.
> Folders ending in `_idlefix_20261004` are the corrected re-runs.

## Hackathon runs (2026-06-07)

| Folder | Run (UTC) | Meaning |
| --- | --- | --- |
| `surface_d5_routed_sim/` | 2026-06-07 00:39 | d5 calibrated simulator, routed Emerald layout, r = 1/3/5. |
| `surface_d3_calibrated_sim/` | 2026-06-07 01:15 | Main d3 calibrated simulator sweep, r = 1/3/5/7, memory Z/X. |
| `surface_d3_iqm_hardware/` | 2026-06-07 01:15 (IQM job `019e9fa6…`, submitted 01:16) | Matching d3 IQM Emerald hardware sweep. |
| `surface_d3_postselected_sim/` | 2026-06-07 01:25 | d3 simulator with low-syndrome postselection (keeps ~50–60% of shots). |

## Post-hackathon runs

| Folder | Run (UTC) | Meaning |
| --- | --- | --- |
| `low_syndrome_postselection_20260608/` | 2026-06-08 14:44 | Postselection comparison (diagnostic; discards shots). |
| `decoder_improvements_20260608/` | 2026-06-08 20:00–20:07 | Baseline vs gated / correlated / ensemble decoders, selected **in-sample** (optimistic). |
| `decoder_validation_20260608/` | 2026-06-08 20:19–20:22 | Holdout and k-fold validation: the in-sample decoder gains do not survive. |
| `best_combined_reported_20260608/` | 2026-06-08 20:32 | Combined postselection + in-sample decoder selection (diagnostic, not a full-shot result). |
| `iqm_baseline_replication_20260608/` | IQM job `019ea8f5…`, submitted 2026-06-08 20:39 | Re-run of the hack-era d3 IQM sweep. Reproduces the saturation at r ≥ 3. |
| `iqm_best_combined_reported_20260608/` | IQM job `019ea8f7…`, submitted 2026-06-08 20:40 | IQM run with the combined postselection recipe. Dynamical decoupling was requested but **not applied** (see `hardware_metadata.csv`). |
| `surface_d3_sim_idlefix_20261004/` | 2026-10-04 10:57 | **Corrected** re-run of the hackathon d3 simulator sweep after the idle-noise fix (decoder selection still in-sample). |
| `surface_d5_sim_idlefix_20261004/` | 2026-10-04 10:57 | **Corrected** re-run of the hackathon d5 routed simulator sweep after the idle-noise fix. |
| `noise_fit_targets_r1/` | hardware r=1 data from 2026-06-08; fit 2026-10-04 | Hardware detector counts and the noise-scale fit that replaced the hand-tuned simulator scales. |
| `surface_d3_sim_fitted_noise_20261004/` | 2026-10-04 11:25 | d3 baseline with the hardware-fitted noise model and plain MWPM (current reference simulator). |
| `surface_d5_sim_fitted_noise_20261004/` | 2026-10-04 11:25 | Routed d5 with the fitted model: above threshold on this layout. |
| `midcircuit_diagnosis_20261004/` | hardware data from 2026-06-08; analysis 2026-10-04 | Round-by-round diagnosis of the hardware failure: data qubits are scrambled once mid-circuit measure/reset begins. Includes the hypothesis table and the probe experiment. |
| `midcircuit_probe_sim_reference_20261004/` | 2026-10-04 11:39–11:40 | Simulator reference for the mid-circuit probe (all three modes agree; expected hardware signature described). |
| `decoder_validation_idlefix_20261004/` | 2026-10-04 11:05–11:07 | Decoder comparison on the corrected simulator: plain MWPM baseline vs in-sample vs k-fold selection. k-fold gives a real gain for memory_x only. |

## Archiving a new sweep

```bash
python scripts/archive_baseline.py results/<sweep>/<timestamp> \
    --output-root baselines/post_hackathon --name <folder> \
    --provenance post_hackathon --title "<title>"
```

The archive README records the provenance label, the git commit that produced the sweep (for sweeps made after this change), and decoded IQM job submit times.

Sweep folders keep `sweep_results.csv`, `sweep_results.json`, `summary.md`, and plots. Comparison folders keep `summary.md`, `comparison_results.csv`, `per_round_fit.csv`, and plots. Hardware folders also keep `hardware_metadata.csv` (job ID, submit time, depth, gate counts, LER, shots).
