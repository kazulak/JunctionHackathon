# Baselines

Compact result summaries preserved from the hackathon work.

These are tracked because `results/` is disposable and ignored.

## Saved Runs

| Folder | Meaning |
| --- | --- |
| `surface_d3_calibrated_sim/` | Main d3 calibrated simulator sweep, rounds 1/3/5/7, memory Z/X. |
| `surface_d3_iqm_hardware/` | Matching d3 IQM hardware sweep, rounds 1/3/5/7, memory Z/X. |
| `surface_d3_postselected_sim/` | D3 simulator with low-syndrome postselection. |
| `surface_d5_routed_sim/` | Latest d5 calibrated simulator sweep using routed Emerald layout. |

Each folder keeps:

```text
sweep_results.csv
sweep_results.json
summary.md
ler_vs_rounds.png
```

The hardware folder also keeps:

```text
hardware_metadata.csv
```

That file preserves job ID, depth, operation counts, LER, and shot count without keeping the full raw measurement tree.
