# Mid-circuit failure diagnosis (2026-10-04)

- Provenance: **Post-hackathon development (not part of the submission)**
- Data: the two post-hackathon IQM Emerald sweeps (jobs `019ea8f5…` and `019ea8f7…`, 2026-06-08), d = 3, r = 1/3/5/7, 2000 shots each
- Tool: `python scripts/diagnose_hardware_rounds.py <sweep dirs> --output <dir>` (tables in `summary.md`, `round_diagnostics.csv`)

## Finding

| | r = 1 | r ≥ 3 |
| --- | ---: | ---: |
| Raw (uncorrected) logical observable flip, both bases | 0.12–0.14 | 0.48–0.52 |
| Deterministic ancillas P(1): Z-type in memory_z, X-type in memory_x | 0.11–0.16 | ≈0.40 in round 2, ≈0.45–0.50 afterwards |
| Detector rate, first layer vs later layers | 0.11–0.16 | 0.41–0.51 |

- r = 1 circuits have no mid-circuit operations. Every r ≥ 2 circuit has mid-circuit measurements plus 8 `reset`s per extra round.
- From the first mid-circuit measure/reset on, the **data qubits** are scrambled in both bases: the raw observable, computed without any decoding, is already ~0.5.
- The non-deterministic ancillas (X-type in memory_z, Z-type in memory_x) show no alternating 0/s pattern, so the reset is not simply a no-op.

So this is a hardware or compilation problem in the mid-circuit operations. It is not a decoder or noise-model problem, and decoder work cannot recover it.

## Hypotheses and how to tell them apart

| Hypothesis | Prediction for the probe experiment below |
| --- | --- |
| Reset takes very long (relaxation-type "wait" reset, or long feedback latency) and the data qubits decohere meanwhile | `measure_reset` fails, `measure` survives, `none` survives |
| Mid-circuit readout disturbs neighbouring data qubits (measurement-induced dephasing or excitation, crosstalk) | `measure_reset` and `measure` both fail, `none` survives |
| A compilation/serialization problem with repeated measurements of the same qubit | `measure` and `measure_reset` fail; also check the IQM job's compiled timeline |

IQM's own pulse library warns that its relaxation-based reset ("reset_wait") destroys the states of other qubits. Which reset implementation Emerald used for `reset` is not visible from the client side.

## Ready-to-run probe experiment (not yet run, needs IQM credits)

Code family `midcircuit_probe` keeps the d = 3 surface-code qubits and pinned Emerald patch, but has **no entangling gates**. The data qubits are prepared in |0⟩ (memory_z) or |+⟩ (memory_x) and left alone. The 8 ancillas repeat `H` followed by one of three operations:

- `measure_reset`: measure, then reset;
- `measure`: measure only;
- `none`: nothing.

At the end the data qubits are measured. The reported "LER" is the probability that any data qubit flipped.

```bash
python scripts/sweep_rounds.py configs/probe_midcircuit_measure_reset_sim.yaml --rounds 1 7 4   # simulator reference
python scripts/sweep_rounds.py configs/probe_midcircuit_measure_reset_iqm.yaml --rounds 1 7 4 --dry-run
python scripts/sweep_rounds.py configs/probe_midcircuit_measure_reset_iqm.yaml --rounds 1 7 4   # needs credits
```

The same pairs exist for `measure` and `none`. `configs/sweep_d3_no_reset_iqm.yaml` runs the full surface code without mid-circuit resets (records virtualized in software) as a fourth comparison.
