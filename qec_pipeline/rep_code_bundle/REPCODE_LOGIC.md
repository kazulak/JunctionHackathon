# Repetition code on IQM Emerald — code, figures, and the logic behind it

## 1. Why a repetition code at all
We first ran the **surface code** on Emerald. It works mechanically but the logical
error is ~32% (d=3) to ~50% (d=5): the 54-qubit chip is **above the surface-code
threshold**, so adding distance makes things *worse*, not better. No decoder fixes that.

The **repetition code** is the opposite: it's shallow (a 1-D chain), only protects
against **bit-flip (X) errors**, and has a **very high threshold**. That's exactly the
regime a NISQ chip can win in — so it's the right code to *demonstrate working QEC*.

## 2. What the repetition code is
- `d` data qubits in a line, with `d-1` ancilla qubits between them.
- Each ancilla measures the **parity of its two neighbors** (a Z-stabilizer) via CNOTs.
- The **logical bit** is the value all data qubits agree on; a single bit-flip shows up
  as a parity mismatch the decoder can locate and undo. It takes `(d+1)/2` correlated
  flips to cause a *logical* error — so higher `d` should mean lower logical error
  (below threshold).
- Qubit count = `2d-1`: d=3->5, d=5->9, d=7->13, d=9->17.

## 3. "Best qubits" = the lowest-error connected chain
A repetition code is a 1-D line, so we pick the **lowest-error connected chain** of
`2d-1` qubits from Emerald's calibration (`calib/emerald_qubit_scores.json` +
`emerald_coupling_map.json`):
- per-qubit cost = readout_err + 2*1q-gate_err + prx_err + 0.5*qnd_fail
- the 5 known-bad qubits (QB9, QB25, QB41, QB46, QB47) are excluded
- greedy: start at the best qubit, always extend to the best unused neighbor.

## 4. The pipeline (same backbone as the surface-code work)
```
stim.Circuit.generated("repetition_code:memory", distance=d, rounds=r)   # the code
   -> stim_to_qiskit(...)          # convert to a Qiskit circuit (handles R/CX/MR/M)
   -> transpile(initial_layout = best chain)   # pin to the best qubits, 0 SWAPs
   -> run on IQM Emerald (50,000 shots)
   -> counts_to_raw(...)           # bitstrings -> (shots, measurements) array
   -> stim m2d converter           # measurements -> detector events + logical observable
   -> PyMatching (MWPM)            # decode detectors -> predicted logical correction
   -> logical error = mean(prediction != true observable)
```
**Safety gate:** before spending any credits we run the circuit through a *noiseless*
simulator and require logical error == 0 (`python rep_code_emerald.py check`). If the
conversion were wrong, this fails — so the hardware numbers are trustworthy.

## 5. Single round vs multi-round
- **Single round (rounds=1)** — `data/rep_d*_shots.npz`: logical error was **0 failures
  in 50,000 at every distance** (< 6e-5). The code is so far below threshold that one
  round is essentially perfect.
- **Multi-round (rounds=d)** — `data/rep_mr_d*_shots.npz`: errors accumulate over rounds,
  so logical error is measurable and we extract **logical error per round**
  (P_total = (1-(1-2*eps)^R)/2). This also breaks the single-round degeneracy.

## 6. Results (real Emerald, multi-round, rounds = d)
| d | rounds | qubits | undecoded | MWPM total | per round |
|---|---|---|---|---|---|
| 3 | 3 | 5  | 0.23% | 0.012% | 0.0040% |
| 5 | 5 | 9  | 0.11% | 0.150% | 0.0300% |
| 7 | 7 | 13 | 2.23% | 0.024% | 0.0034% |
| 9 | 9 | 17 | 2.30% | 1.540% | 0.1735% |

**Headline:** logical error per round is **0.003–0.17%** (99.8–99.997% per-round logical
fidelity) — *working QEC*, vs the surface code's 32% on the same chip.

## 7. Honest caveat (see `rep_code_suppression.png`)
The per-round curve is **not monotonic** — it bounces. Two real reasons:
1. **Different chain per distance.** Longer chains are forced onto worse qubits — note
   `undecoded` jumps to ~2.3% for d=7/d=9 vs ~0.1% for d=3/d=5. So chain *quality*
   varies with length and **confounds the distance effect**.
2. **Small-number statistics:** totals are 6 / 75 / 12 / 770 failures in 50k.

Deeper point: Emerald is so far below the repetition-code threshold that logical error is
dominated by **which physical qubits** a chain lands on, not by code distance — the
distance-suppression is below the chain-to-chain noise.

**To get the clean, monotonic Lambda>1 suppression curve:** use **nested chains** (one
best core, extended symmetrically for each d) so increasing distance adds qubits to the
*same* line, plus more shots. That isolates the distance effect.

## 8. Files
- `rep_code_emerald.py` — the experiment (`check` = noiseless sanity, `run` = hardware)
- `surface_code.py`, `internal_helpers.py` — the Stim->Qiskit converter it imports
- `calib/` — Emerald calibration (coupling map + per-qubit scores) for chain selection
- `data/rep_d*_shots.npz` — single-round raw shots; keys: `raw` (shots x meas, uint8),
  `chain` (physical qubit indices)
- `data/rep_mr_d*_shots.npz` — multi-round raw shots; keys: `raw`, `chain`, `rounds`
- `rep_code_suppression.png` — per-round logical error vs distance

## 9. Reproduce
```bash
pip install numpy stim pymatching qiskit qiskit-aer iqm-client[qiskit] matplotlib
python rep_code_emerald.py check          # free, verifies the conversion
export IQM_TOKEN=...                       # then, to re-run on hardware:
python rep_code_emerald.py run
```
Decode saved shots without hardware: load `data/rep_mr_d{d}_shots.npz['raw']` and call
`decode(raw, d, rounds=d)` from `rep_code_emerald.py`.
