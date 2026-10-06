# Calibration-informed simulation

`noise.model: iqm_calibration` builds a Stim noise model from an IQM calibration dump and the selected qubit mapping.
It is **calibration-informed and fitted to r=1 hardware**, not a full calibration: see "Limits" below and [ERRATA.md](../ERRATA.md) E2.

```text
IQM calibration dump (configs/calibration/*.json)
-> select mapped qubits/couplers
-> inject per-qubit/per-coupler Pauli noise into the Stim circuit
-> sample locally
-> decode detector events
-> LER vs rounds
```

## Noise model

| Source | Calibration field | Stim channel |
| --- | --- | --- |
| One-qubit gates (H/X/Z) | `rb.prx` (or `rb.clifford`) fidelity, converted ×1.5 to a Pauli probability | `DEPOLARIZE1` after the gate |
| Two-qubit gates (CX/CZ) | `irb.cz` (or `rb.clifford` two-qubit) fidelity, converted ×1.25 | `DEPOLARIZE2` after the gate |
| Readout | mean of `ssro` `error_0_to_1` and `error_1_to_0`; mid-circuit readouts use `ssro.measure.*`, final readouts `ssro.measure_fidelity.*` | *classical* flip of the recorded bit, Stim `M(p)` (matters for feed-forward and no-reset circuits) |
| Idle | T1 and T2 (`idle_t2: ramsey` without DD, `echo` with DD), Pauli-twirled for `round_duration_s` | `PAULI_CHANNEL_1` at every TICK, 1/ticks-per-round of a round each |
| Non-QND readout | `1 − min(qndness_0, qndness_1)` | flip **after** a measurement, only if the qubit is reused without reset (never in reset-based memory circuits) |
| Reset | not in IQM dumps | none (recorded as `reset_error_available: false`) |
| Routed (non-adjacent) CX | combined error of the shortest coupler path × `route_error_multiplier` | `DEPOLARIZE2` |

The ×1.5 / ×1.25 factors convert average gate infidelity r to the probability p of a uniformly random non-identity Pauli (r = p·d/(d+1)). Turn them off with `rb_to_pauli: false`.

## Mid-circuit reset strategy (`code.mid_circuit_reset`)

| Strategy | Stim encoding | IQM implementation | Round on Emerald (Pulla, grouped readout) |
| --- | --- | --- | ---: |
| `reset` (default) | `MR` | measure + Qiskit `reset` (second measurement + feedback) | 5.8 µs |
| `feedforward` | `M` + `CX rec[-k] q` | measure + conditional X (`cc_prx`) | 1.75 µs |
| `none` | `M`, detectors two rounds apart | measure only | 1.3 µs |

Set `noise.options.round_duration_s` to the matching duration. With feed-forward or no reset, a readout
classification error flips detectors two rounds apart (Gehér et al., arXiv:2408.00758); the circuit and its
detector error model encode this.

## Fitted scales

The hardware configs use `two_qubit_scale: 1.5` (2.0 before the readout/idle corrections), fitted to IQM Emerald hardware at r = 1 (`baselines/post_hackathon/noise_fit_targets_r1/`). Readout and idle stay at their calibration values because r = 1 data cannot separate them from two-qubit error.

Re-fit after new hardware runs:

```bash
python scripts/fit_noise_to_hardware.py export-targets --config configs/sweep_d3_baseline_sim.yaml \
    --run results/<hardware sweep>/<ts>/runs/<..._rounds_1>/<ts> --output <targets.json>
python scripts/fit_noise_to_hardware.py fit --config configs/sweep_d3_baseline_sim.yaml --targets <targets.json>
```

## Options

```yaml
noise:
  model: iqm_calibration
  calibration_file: configs/calibration/emerald_2026-06-06T06_08_52Z.json
  options:
    apply_idle: true
    two_qubit_scale: 1.5        # fitted; other *_scale options default to 1.0
    round_duration_s: 1.29e-6   # per strategy, from scripts/pulla_schedule_report.py
    idle_t2: echo               # ramsey without DD
    rb_to_pauli: true           # default for IQM observation sets
    idle_model: pauli_twirl     # or depolarize
    route_error_multiplier: 1.0
```

`scripts/search_calibrated_sim.py` halves one noise source at a time (an error budget). It is a sensitivity study and must not be used to choose scales.

## Commands

```bash
python scripts/sweep_rounds.py configs/sweep_d3_baseline_sim.yaml --rounds 1 7 4
python scripts/sweep_rounds.py configs/sim_iqm_emerald_surface_d5_calibrated.yaml --rounds 1 5 3
```

## Limits

- The fit to r = 1 hardware is poor in absolute terms: uniform scales cannot reproduce the per-detector rates, which range from 0.05 to 0.25.
- The model has no leakage, crosstalk, drift, measurement-induced dephasing, or pulse-level timing.
- With the corrected hardware design it predicted 0.039 / 0.059 error per round; hardware gave 0.033 / 0.040 (`baselines/post_hackathon/hw_d3_noreset_dd_20261004/model_comparison`). It is pessimistic for memory_x.
