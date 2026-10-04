# Post-hackathon runs

Everything in this folder was run **after** the Junction Quantum Hack 2026 submission (2026-06-08 onward).
None of it is part of the hackathon entry.

Folders dated `20260608` were produced before the October 2026 audit and share its known issues (see [ERRATA.md](../../ERRATA.md)):

- simulator results include the idle-noise scaling bug;
- `decoder_improvements_20260608` and `best_combined_reported_20260608` select decoder candidates in-sample, so their gains are optimistic (`decoder_validation_20260608` shows they do not survive holdout/k-fold);
- postselected results discard roughly 40–75% of shots and are diagnostics, not full-shot logical-memory results.

Corrected runs will be added here with an explicit date and note.
