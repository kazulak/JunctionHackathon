# Repetition Code Explanation

## What It Is

The repetition code protects one classical bit against bit-flip errors.

For distance `d=3`:

```text
data -- ancilla -- data -- ancilla -- data
 q0       q1       q2       q3       q4
```

The ancillas repeatedly measure neighbor parity:

```text
Z0 Z2
Z2 Z4
```

If one data qubit flips, one or two parity checks change. Across many rounds, these parity changes form a detector-event pattern. PyMatching decodes that pattern and predicts whether the final logical bit flipped.

The logical observable is the final value of the encoded bit. Stim defines the detectors and observable exactly; the pipeline converts raw measurements to detector events with Stim's measurement-to-detector converter.

## Why We Added It

The surface-code path is theoretically stronger, but on our current hardware runs it saturates:

```text
d=3 surface code, Emerald, rounds >= 3: LER about 0.48-0.50
```

The repetition code is less ambitious but much shallower:

```text
d=3 repetition code: 5 qubits
round 50 circuit: 200 logical CX gates before transpile
transpiled: 219 CZ gates, 0 literal SWAP gates
```

That makes it a good hardware-optimized demonstration after identifying that the full surface-code schedule is too noisy.

## Why The LER Is So Low

Main reasons:

- It protects only one error channel, not arbitrary X/Z errors.
- It uses 5 qubits instead of 17 or 49.
- The circuit is a 1D chain with simple nearest-neighbor parity checks.
- The decoder gets many rounds of syndrome history.
- The selected Garnet layout transpiles with 0 literal SWAP gates.

Fresh Garnet hardware sweep:

```text
artifact: results/final_rep_code_iqm_rounds_sweep/20260607T062249Z
rounds 1:  total LER 0.00255 +/- 0.00036
rounds 9:  total LER 0.02245 +/- 0.00105
rounds 17: total LER 0.02800 +/- 0.00117
rounds 26: total LER 0.03325 +/- 0.00127
rounds 34: total LER 0.02450 +/- 0.00109
rounds 42: total LER 0.01460 +/- 0.00085
rounds 50: total LER 0.01630 +/- 0.00090
rounds 50 per-round LER: 0.000331 +/- 0.000018
```

## Why It Looks Suspicious

The long-round curve is not monotonic. It improves after round 26 in the fresh run.

Possible explanations:

- More syndrome history can help PyMatching distinguish data errors from measurement errors.
- The run is sensitive to QPU drift and batch execution order.
- Reset/readout transients may dominate short and medium circuits differently than long circuits.
- Our Stim-level noise model is still approximate and had to be scaled to match hardware.

So the honest claim is:

```text
We demonstrated a low-depth repetition-code QEC path with strong Garnet LER.
We did not demonstrate full surface-code logical memory below threshold.
```

## Sanity Check

Noiseless Stim checks:

```text
d=3 repetition code, rounds 1:  LER 0.0
d=3 repetition code, rounds 9:  LER 0.0
d=3 repetition code, rounds 50: LER 0.0
```

This verifies the detector/observable/decoder convention for the generated code.
