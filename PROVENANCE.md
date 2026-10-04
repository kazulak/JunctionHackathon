# Provenance

This repository holds two things that should not be confused:

1. **The Junction Quantum Hack 2026 submission** by team *gate_crushers* (IQM Quantum Error Correction challenge, 5–7 June 2026). It is frozen.
2. **Post-hackathon development** on `main` (from 8 June 2026 onward). It was not part of the submission.

Everything below can be re-checked with:

```bash
git fetch --tags
python scripts/verify_submission.py
```

## Where the submission lives

| What | Reference |
| --- | --- |
| Submission code | commit `16e86b1`, tag **`hackathon-submission-2026-06-07`** |
| Checkpoint with submission files | commit `3cfa714`, tag **`junction-quantum-hackathon-final-2026`**, branch `checkpoint/junction-quantum-hackathon-final` |
| Submission archive + slides | [GitHub release](https://github.com/kazulak/JunctionHackathon/releases/tag/junction-quantum-hackathon-final-2026) |
| Submission zip SHA-256 | `248c62a0072bebed92ce9b04b375af564c6d484191e5e372c9fabc5dd522260c` |

Both tags and `checkpoint/*` branches are protected by repository rulesets (no deletion, no moving, no force-push).

`3cfa714` was committed on 2026-06-08, after the event. It adds only the submission zip and slides on top of `16e86b1`; the code tree is identical.
All 99 files that exist in both the zip and `16e86b1` are byte-identical (line endings normalized). The zip additionally contains 8 gitignored `.npz` shot-data files; git additionally contains 31 files of provided reference material under `archive/`.

Some hackathon work (the repetition-code route, `judge_results/`, the judge pack script) was removed from `main` in `feeee3e`. It exists only on the tags and in the release.

## Timeline

Push times are GitHub's server-side record (`gh api repos/kazulak/JunctionHackathon/activity`), so they cannot be changed by rewriting local commit dates. Commit dates are local (CEST, UTC+2).

### Challenge baseline (organizers)

| Commits | Author | Dates (CEST) |
| --- | --- | --- |
| `5eae04f` … `6eeafb4` (13 commits) | Niklas Steinmann / Nik-SteinFraunh (Fraunhofer FOKUS) | 2026-06-04 11:30 – 2026-06-05 20:39 |

The original baseline repository (`Nik-SteinFraunh/JunctionHackathon`) is no longer available.

### Hackathon (team gate_crushers)

| Commits | Committed (CEST) | Pushed to GitHub (UTC) |
| --- | --- | --- |
| `c922bb0` minimal simulator demo … `2b5fab2` update markdown files | 2026-06-06 11:57 – 15:30 | 2026-06-06 13:30:23 |
| `c1554b0` clean structure and some tests | 2026-06-06 16:46 | 2026-06-06 14:46:29 |
| `23ac5a0` Baseline | 2026-06-06 19:19 | 2026-06-06 17:19:16 |
| `e1cb593` improvements - work in progress | 2026-06-06 23:10 | 2026-06-06 21:10:06 |
| `04a3ee0` … `9e16c6e` Updated markdowns and auto decoder | 2026-06-07 01:59 – 04:22 | 2026-06-07 02:22:28 |
| **`16e86b1` final project** | 2026-06-07 08:42 | **2026-06-07 06:42:31** |

Submission archive `gate_crushers_submission_20260607_085338.zip` was created 2026-06-07 08:53:38 CEST from this state.

### After the hackathon

| Commit | Committed (CEST) | Pushed (UTC) | Content |
| --- | --- | --- | --- |
| `3cfa714` | 2026-06-08 15:29 | 2026-06-08 13:30:38 | Checkpoint: adds submission zip and slides only |
| `feeee3e` | 2026-06-08 16:23 | 2026-06-08 14:23:34 | Cleanup; archives hack-era runs into `baselines/` |
| `745cc76` | 2026-06-08 16:50 | 2026-06-08 14:50:17 | Research roadmap, postselection experiments |
| `5c58858` | 2026-06-08 22:50 | 2026-06-08 20:53:39 | Decoder experiments, second IQM runs |
| PR #1 onward | 2026-10 | — | Audit follow-up (CI, provenance, fixes) |

## IQM hardware jobs

IQM job IDs are UUIDv7 values, which embed their submit time.

| Job ID | Submitted (UTC) | Period | Archived in |
| --- | --- | --- | --- |
| `019e9fa6-c559-77a0-821e-462fcebccfba` | 2026-06-07 01:16:07 | Hackathon | `baselines/hackathon_2026-06-07/surface_d3_iqm_hardware` |
| `019ea0bf-be09-7130-b3a5-ac13e7da9c4a` | 2026-06-07 06:23:01 | Hackathon (repetition code, Garnet) | submission zip only (`judge_results/tables/swap_depth_summary.csv`) |
| `019ea8f5-df66-7b92-bf18-4080bea4abc3` | 2026-06-08 20:39:06 | Post-hackathon | `baselines/post_hackathon/iqm_baseline_replication_20260608` |
| `019ea8f7-5112-7b60-a001-7003aba9fb4d` | 2026-06-08 20:40:40 | Post-hackathon | `baselines/post_hackathon/iqm_best_combined_reported_20260608` |

## Results

- [`baselines/hackathon_2026-06-07/`](baselines/hackathon_2026-06-07/) holds runs made during the hackathon.
- [`baselines/post_hackathon/`](baselines/post_hackathon/) holds everything later.
- New runs record the git commit that produced them (`provenance.json` per run, provenance line in every summary).

## Credits

- **Challenge baseline:** Niklas Steinmann (Fraunhofer FOKUS) and the Junction Quantum Hack 2026 / IQM organizers. The baseline files are unlicensed and are used here for the challenge; see [NOTICE](NOTICE).
- **Hackathon submission:** team *gate_crushers*. All commits in this repository were made by Tomasz Kazulak. The repetition-code route in the submission was distilled from a teammate's code, as stated in the submission documents.

## GitHub fork relationship

GitHub lists this repository as a fork of `ChaosCodeSpirit/JunctionHackathon`. That repository is a separate project. This repository's history shares only the organizer baseline commits with it (`5eae04f` … `6eeafb4`) and contains none of its other commits. A request to detach the fork has been prepared.

## Known issues

Issues found after the hackathon that affect submitted or archived numbers are listed in [ERRATA.md](ERRATA.md). The tags are intentionally left unchanged.
