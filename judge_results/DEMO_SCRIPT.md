# Two-Minute Demo Script

## 0:00-0:20: Goal

Show the YAML-driven QEC pipeline and the final LER evidence. The key point is that the same structure runs simulator and IQM hardware, then writes raw artifacts and plots.

## 0:20-0:45: Pipeline

Open `README.md` and show:

```text
YAML -> Stim circuit -> simulator/IQM -> detector events -> decoder -> LER
```

Then open `configs/final_rep_code_iqm.yaml` and point at `code.family`, `backend.name`, `decoder.name`, and `mapping.hardware_patch`.

## 0:45-1:15: Evidence

Open `judge_results/plots/ler_vs_rounds_combined.png`.

Say:

```text
Surface code is functional, but repeated hardware rounds saturate near 0.5 LER.
The final low-depth repetition-code path avoids that saturation on Garnet.
For 50 rounds we measured total LER 0.0163 +/- 0.0009.
Converted per round, that is 0.000331 +/- 0.000018.
```

## 1:15-1:40: Hardware-Aware Part

Open `judge_results/tables/swap_depth_summary.csv`.

Say:

```text
We record job IDs, depth, two-qubit counts, selected mapping, and SWAP evidence.
Curated hardware runs have 0 literal transpiled SWAP gates.
The long repetition-code run has 219 transpiled two-qubit gates versus 200 logical two-qubit gates.
```

## 1:40-2:00: Honest Caveat

Say:

```text
The repetition code protects one channel, not full surface-code memory.
The important engineering result is the modular pipeline plus the diagnosis:
full surface-code rounds currently fail because the hardware effects are not captured by the simple Stim noise model.
Next steps are PulLA/DD compilation, better reset/readout/leakage noise, and calibrated decoder weights.
```

## Commands

Regenerate this judge pack:

```powershell
.\.venv\Scripts\python.exe scripts\build_judge_pack.py
```

Run the final simulator/hardware pair:

```powershell
.\.venv\Scripts\python.exe scripts\sweep_rounds.py configs\final_rep_code_sim.yaml --rounds 1 50 7
.\.venv\Scripts\python.exe scripts\sweep_rounds.py configs\final_rep_code_iqm.yaml --rounds 1 50 7
```
