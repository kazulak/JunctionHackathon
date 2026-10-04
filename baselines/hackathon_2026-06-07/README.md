# Hackathon runs (Junction Quantum Hack 2026)

These four runs were made on 2026-06-07 (UTC), during the hackathon and before the submission was pushed at 06:42 UTC.
They were copied here from the local `results/` folder after the event (commit `feeee3e`, 2026-06-08). The numbers are unchanged.

The submission itself, including its judge tables, is frozen on tag `junction-quantum-hackathon-final-2026`
and in the [GitHub release](https://github.com/kazulak/JunctionHackathon/releases/tag/junction-quantum-hackathon-final-2026).

Known issues (see [ERRATA.md](../../ERRATA.md)):

- Simulator runs (`*_sim`) include the idle-noise scaling bug, so LER for r ≥ 3 is too high.
- The `surface_d3_*` runs used `pymatching_auto` with in-sample candidate selection, which is slightly optimistic.
- The "calibrated" simulator used hand-tuned scales (`qnd_scale: 0`, `idle_scale: 0.5`).
