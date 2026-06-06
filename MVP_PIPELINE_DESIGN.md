# MVP Pipeline Architecture and Workflow

This document is a planning artifact only. It describes the proposed MVP architecture, the current state of the repository, the missing work, and the workflow we should implement for the challenge.

The challenge target is an offline quantum error correction memory experiment:

```text
Stim circuit -> Qiskit -> IQM Resonance/QPU -> raw measurements
raw measurements -> syndrome extraction -> decoder -> logical error rate
```

The goal is not just to produce a number. The goal is to show a correct, inspectable experiment with enough diagnostics to explain why the logical error rate is good, bad, or improving.

## 1. MVP Pipeline Architecture Design

### MVP Scope

The MVP should be a distance-3 rotated surface code memory experiment on IQM Emerald, with both simulation and hardware paths using the same experiment definition.

Minimum output:

- Logical error rate, or LER, with 1-sigma statistical uncertainty.
- Syndrome diagnostics: syndrome weight per shot and per-detector firing rates.
- Circuit diagnostics: number of qubits, number of detectors, measurement count, circuit depth, two-qubit gate count, SWAP count.
- Experiment metadata: code distance, rounds, memory basis, reset mode, backend, shots, mapping, decoder, noise model.
- Saved raw outputs so that decoding and plotting can be rerun without spending more QPU time.

Recommended MVP choices:

- Code family: rotated surface code.
- Distance: start with distance 3.
- Memory basis: start with Z memory, then add X memory if time permits.
- Circuit framework: Stim as source of truth, converted to Qiskit for hardware.
- Decoder: PyMatching/MWPM first.
- Execution: local simulation first, then IQM Resonance hardware.
- Mapping: automatic Qiskit transpilation for first smoke test, custom Emerald layout for serious run.
- Noise model: simple depolarizing model for local MVP, then calibration-weighted model for improved hardware decoding.

### Architecture Diagram

```text
                         +---------------------+
                         | Experiment config   |
                         | d, rounds, basis,   |
                         | shots, reset mode,  |
                         | backend, patch      |
                         +----------+----------+
                                    |
                                    v
                         +---------------------+
                         | Circuit generator   |
                         | Stim source circuit |
                         +----------+----------+
                                    |
                 +------------------+------------------+
                 |                                     |
                 v                                     v
      +---------------------+              +----------------------+
      | Simulation circuit  |              | Hardware circuit     |
      | with noise model    |              | noiseless Qiskit     |
      +----------+----------+              +----------+-----------+
                 |                                    |
                 v                                    v
      +---------------------+              +----------------------+
      | Stim sampler        |              | Qiskit transpilation |
      | or Aer baseline     |              | layout/DD optional   |
      +----------+----------+              +----------+-----------+
                 |                                    |
                 v                                    v
      +---------------------+              +----------------------+
      | simulated raw meas  |              | IQM Resonance job    |
      +----------+----------+              +----------+-----------+
                 |                                    |
                 +------------------+-----------------+
                                    |
                                    v
                         +---------------------+
                         | Syndrome extraction |
                         | det_events, obs     |
                         +----------+----------+
                                    |
                                    v
                         +---------------------+
                         | Decoder             |
                         | PyMatching first    |
                         +----------+----------+
                                    |
                                    v
                         +---------------------+
                         | Analysis/reporting  |
                         | LER, plots, tables  |
                         +---------------------+
```

### Pipeline Modules

#### Experiment configuration

Use one explicit configuration object or dictionary that drives both simulation and hardware runs.

Required fields:

- `distance`: code distance, initially `3`.
- `rounds`: number of stabilizer measurement rounds.
- `basis`: `memory_z` or `memory_x`.
- `shots`: number of shots.
- `reset_mode`: `reset` or `no_reset`.
- `backend`: `simulator`, `emerald`, `garnet`, or another supported QPU.
- `patch`: physical qubit patch or mapping identifier.
- `noise_model`: simple depolarizing, calibration-based, or none.
- `decoder`: `pymatching`, later maybe `ising`, `union_find`, or `bp`.

This keeps the architecture flexible enough for different QPUs, different patches on Emerald, and possible non-surface-code experiments later.

#### Circuit generation

Stim should be the MVP source of truth because it can carry:

- Qubit coordinates.
- Detector definitions.
- Logical observable definitions.
- Noise annotations for simulation.
- A detector error model for PyMatching.

The shortest MVP path is to generate a Stim rotated surface-code memory circuit using Stim's built-in generated circuit family, then preserve that circuit as the reference for syndrome extraction and decoding.

We should not start with a pure Qiskit circuit unless we also write and test manual detector bookkeeping. Pure Qiskit may be useful later for PulLA or custom IQM-native circuits, but it makes the first correct MVP harder.

Circuit generation should support:

- Distance 3 first, distance 5 later.
- Z and X memory experiments.
- One or more stabilizer rounds.
- Reset and no-reset variants.
- Noiseless circuit for hardware execution.
- Noisy circuit for simulation and decoder graph generation.

#### Stim to Qiskit conversion

The existing converter should remain the first bridge into Qiskit. It already handles:

- Dense qubit reindexing.
- Dropping Stim-only noise and annotation instructions.
- Measurement order preservation.
- `MR` as measure-then-reset.

For MVP correctness, this conversion needs validation on small circuits:

- Measurement count must match `stim_circuit.num_measurements`.
- The Qiskit classical-bit order must match the order expected by Stim's measurement-to-detector converter.
- All gates used by generated circuits must be supported by the converter.

#### Hardware mapping and transpilation

The first smoke test can use Qiskit's automatic mapping. The judged result should use a custom Emerald mapping where the rotated surface-code patch aligns with a 5x5 region of the hardware graph.

Why this matters:

- Surface-code circuits are dominated by repeated data-ancilla two-qubit interactions.
- Automatic routing can insert SWAPs if the abstract connectivity does not match the QPU.
- SWAPs add depth and two-qubit error, directly hurting LER.
- Proving a low or zero SWAP count addresses a major judging criterion.

Required mapping diagnostics:

- Physical qubit assignment table.
- Native vs non-native two-qubit interactions.
- SWAP count after transpilation.
- Circuit depth before and after transpilation.
- Two-qubit gate count before and after transpilation.

#### Execution backends

Use one common interface for execution:

```text
run_experiment(config, circuit) -> raw_measurements, metadata
```

Backends:

- `stim_simulator`: fast local sanity checks with a Stim noise model.
- `qiskit_aer`: optional, useful if we want to validate Qiskit conversion.
- `iqm_resonance`: real hardware via IQMProvider.

The hardware execution should save:

- Qiskit transpiled circuit metadata.
- Backend name and calibration snapshot if available.
- Job ID.
- Counts.
- Expanded raw measurement array.
- Stim circuit text used for conversion.
- Experiment config.

#### Syndrome extraction

The MVP should use Stim's `compile_m2d_converter()` because the generated Stim circuit already contains detector and observable definitions.

Inputs:

- Raw measurement array with shape `(shots, num_measurements)`.
- Reference Stim circuit with matching measurement record and detector definitions.

Outputs:

- `det_events`: boolean array with shape `(shots, num_detectors)`.
- `obs_flips`: boolean array with shape `(shots, num_observables)`.
- Diagnostics: syndrome weight per shot, detector firing rates.

This module is a strong part of the current repo and should be reused.

#### Decoder

The MVP decoder should be PyMatching.

Expected decoder flow:

```text
noisy Stim circuit -> detector error model -> PyMatching graph
det_events -> predicted observable corrections
predicted corrections XOR observed observable flips -> logical failures
mean(logical failures) -> LER
sqrt(LER * (1 - LER) / shots) -> 1-sigma uncertainty
```

The decoder should return both result values and enough metadata to explain the result:

- LER.
- Statistical uncertainty.
- Number of shots.
- Number of logical failures.
- Decoder name and parameters.
- Noise model used to build decoder weights.

Initial decoder weights can come from a simple depolarizing model. A stronger version should use Resonance calibration data to weight edges, because hardware noise is not uniform across qubits or couplers.

#### Analysis and reporting

The challenge organizers explicitly value documentation and showing the work. The pipeline should therefore produce human-readable outputs automatically.

Recommended outputs:

- `results/experiments/<timestamp>/config.json`.
- `results/experiments/<timestamp>/stim_circuit.stim`.
- `results/experiments/<timestamp>/transpiled_circuit.qasm` or equivalent.
- `results/experiments/<timestamp>/raw_counts.json`.
- `results/experiments/<timestamp>/metrics.json`.
- `results/experiments/<timestamp>/summary.md`.

Recommended summary tables:

- Simulation baseline by distance, rounds, and noise level.
- Hardware runs by backend, patch, basis, and reset mode.
- Transpilation metrics by mapping strategy.
- Detector firing-rate table highlighting hot detectors.
- LER comparison before and after improvements.

### Extension Architecture

The architecture should leave room for advanced features without making the MVP depend on them.

#### Custom error model

This is the most valuable extension after the MVP because it improves both simulation credibility and decoder quality.

Start simple:

- Single-qubit depolarizing probability.
- Two-qubit depolarizing probability.
- Measurement flip probability.
- Reset error probability.
- Idle/decoherence probability per round.

Then make it calibration-aware:

- Use T1/T2 for idle errors.
- Use single-qubit and two-qubit calibration fidelities.
- Use readout fidelities.
- Use coupler-specific error rates.
- Build decoder weights from these probabilities.

This gives us a clear story: "simple noise model -> calibration-aware noise model -> LER improvement or diagnosis".

#### Multiple patches and multiple QPUs

The same distance-3 experiment can be run on:

- Different 5x5 regions of Emerald.
- Emerald vs Garnet if access and topology allow.
- Reset vs no-reset variants on the same backend.

This is likely easier and lower risk than PulLA or NVIDIA Ising, while still scoring under hardware flexibility and experimental diagnosis.

#### IQM client-side improvements and PulLA

Use IQM's client-side tools only after the gate-level path is stable.

Potential improvements:

- Dynamical decoupling for idle data qubits.
- Custom transpilation/pass manager settings.
- Pulse-level compilation with PulLA.

PulLA is high value but may require organization access and extra mentor support. It should be treated as an advanced branch, not the MVP critical path.

#### NVIDIA Ising decoder/predecoder

The NVIDIA Ising route is valuable if the core MVP works first. It is not a low-risk first path.

Expected extra work:

- Understand the Ising package's `MemoryCircuit` abstraction.
- Adapt circuit generation because it may use a different Stim-to-Qiskit route.
- Build or adapt a compatible error model.
- Connect Ising outputs to our standard decoder result interface.
- Compare Ising/predecoded results against PyMatching on the same shots.

Recommended position:

- MVP decoder: PyMatching.
- Stretch decoder: NVIDIA Ising, only after end-to-end simulation and hardware data exist.
- Documentation story: explain why Ising is promising, what integration required, and whether it improved LER or runtime.

#### Alternative code families

The challenge allows alternatives such as color codes. We should keep this as a later research branch.

Reason:

- The provided repo and challenge text are aligned around surface code.
- Stim and PyMatching make surface-code MVP fast.
- Alternative codes increase detector, mapping, and decoder complexity.

Architecture requirement:

- Keep `code_family` in config.
- Do not hard-code surface-code assumptions outside circuit generation, mapping, and analysis labels.

## 2. What We Already Have, What Needs Upgrades, and What We Need To Write

### Current Repository State

| File or folder | What exists now | Needs upgrade | Need to write ourselves |
| --- | --- | --- | --- |
| `README.md` | Challenge overview, pipeline description, judging criteria, and provided-vs-missing functionality. | Encoding appears corrupted in some characters, but content is readable. Could be cleaned for presentation later. | Nothing for MVP architecture. |
| `UsefulResources.md` | Links and notes for Resonance, PulLA, client-side libraries, notebooks, calibration data, and IQM resources. | Could be summarized into our own final documentation. | Nothing urgent. |
| `requirements.txt` | Pins Qiskit, Qiskit Aer, Stim, PyMatching, NumPy, IQM client, and IQM qubit selector. | Verify installability in our environment. Add plotting/data packages only if actually used. | Dependency lock or setup instructions. |
| `surface_code.py` | Contains `stim_to_qiskit`, `get_circuit_info`, default noise constants, and placeholders for circuit generation, simulation, hardware, and decoding sections. | Implement missing `make_stim_circuit`, maybe remove unused `make_qiskit_circuit` until needed, validate converter against generated circuits, clean imports. | Main circuit generator, simulation entry point, decoder integration, config handling. |
| `extract_syndromes.py` | Good starting implementation using Stim's measurement-to-detector converter. Returns detector events, observable flips, raw measurements, and diagnostics. | Re-enable or replace summary printing through structured reporting. Validate shapes and measurement order. | Additional plotting/reporting around detector firing rates. |
| `run_on_hardware.py` | Has IQMProvider connection flow, Qiskit transpilation, job submission, counts extraction, and counts-to-array conversion. | `token` parameter is ignored in favor of global `TOKEN`; `no_reset` is not passed into circuit generation; mapping is built but not used; metadata is not saved. | Robust hardware runner, result persistence, dry-run transpilation mode, backend metadata capture. |
| `internal_helpers.py` | Has qubit classification, measurement order extraction, and Qiskit counts conversion. | Duplicate unreachable return in `get_qubit_lists`; needs tests for coordinate assumptions and bit order. | Small validation helpers for circuit/measurement consistency. |
| `build_emerald_qubit_rotated.py` | Contains detailed comments and a `print_qubit_map` diagnostic idea. `build_emerald_qubit_map` is still empty. | Imports `surface_code_stim`, which does not exist under that filename. `print_qubit_map` calls `build_emerald_qubit_map` with parameters the current signature does not accept. | Actual Emerald 5x5 layout builder and coupling-map verification. |
| `iqm_utils/` | Notebooks and a calibration-data script from IQM resources. | Convert only the useful parts into reusable helpers; avoid depending on notebooks during the MVP pipeline. | Calibration import helper and maybe patch-selection tooling. |
| `__init__.py` | Re-exports internal helpers. | May need package cleanup once modules stabilize. | Nothing urgent. |

### What Is Already Strong Enough To Reuse

- The high-level challenge framing in `README.md`.
- Stim-to-Qiskit conversion as a first implementation base.
- Stim-based syndrome extraction.
- Qiskit counts-to-measurement-array conversion idea.
- IQMProvider hardware connection pattern.
- IQM notebooks as examples for Resonance setup, routing, and calibration.

### What Needs Upgrades Before a Serious Run

- Fix module naming/import mismatch around `surface_code_stim` vs `surface_code.py`.
- Implement the circuit generator.
- Validate measurement order end to end.
- Implement the decoder.
- Implement or disable custom mapping cleanly.
- Save experiment artifacts and metadata.
- Add simulation baseline before submitting QPU jobs.
- Add tests or sanity checks for each pipeline boundary.

### What We Need To Write By Ourselves

#### Required for MVP

- A real experiment driver that runs:
  - circuit generation,
  - simulation or hardware execution,
  - syndrome extraction,
  - decoding,
  - reporting.
- `make_stim_circuit(distance, rounds, basis, noise_model, reset_mode)`.
- `decode_hardware_results(...)` or a more general `decode_results(...)`.
- A PyMatching graph construction path from the Stim detector error model.
- LER and statistical uncertainty aggregation.
- Result persistence into a structured folder.
- A short final demo notebook or script.

#### Important for competitive quality

- Custom Emerald qubit mapping for distance-3 rotated surface code.
- SWAP/depth/two-qubit-gate diagnostics before hardware submission.
- Calibration-aware noise model.
- Calibration-weighted decoder edges.
- Multi-patch or multi-QPU experiment comparison.
- Reset vs no-reset comparison.
- Clean final Markdown report with figures and tables.

#### Stretch work

- Dynamical decoupling integration.
- PulLA pulse-level compilation experiment.
- NVIDIA Ising predecoder integration.
- Distance-5 experiment if hardware time and topology allow.
- Alternative decoder comparison: union-find, belief propagation, or Ising.
- Alternative code family exploration, such as color code.

## 3. Workflow We Should Implement

### Workflow Goal

Every experiment should be reproducible from a single configuration and should produce enough artifacts to rerun analysis without another hardware job.

The workflow should be:

```text
configure -> generate -> validate -> simulate -> transpile -> run -> extract -> decode -> report
```

### Phase 0: Repository and Environment Sanity

Do this before writing the experimental logic:

- Install and verify requirements.
- Confirm imports work.
- Fix module naming mismatch.
- Decide the public entry point, for example `run_experiment.py` or a notebook.
- Keep a simple `results/` output structure out of source code logic.

Sanity checks:

- Can import Stim, Qiskit, PyMatching, NumPy.
- Can import local modules.
- Can generate one trivial Stim circuit.
- Can convert one generated circuit to Qiskit.

### Phase 1: Local Simulation MVP

Purpose: prove correctness without spending QPU time.

Steps:

1. Build a distance-3 rotated surface-code memory-Z Stim circuit.
2. Add a simple noise model for simulation.
3. Sample raw measurements locally.
4. Convert raw measurements into detector events and observable flips.
5. Build a PyMatching decoder from the Stim detector error model.
6. Decode all shots.
7. Compute LER and uncertainty.
8. Save summary metrics and raw arrays.

Required validation:

- Number of measurements matches the raw measurement array width.
- Number of detectors matches `det_events.shape[1]`.
- Number of observables is nonzero and matches decoder output width.
- LER changes sensibly when noise probability changes.
- With near-zero noise, LER is near zero.

Expected deliverable:

- A small Markdown table with LER for a few noise levels and rounds.

### Phase 2: Qiskit Conversion and Transpilation Dry Run

Purpose: prove the hardware circuit is executable and not accidentally deep.

Steps:

1. Generate the noiseless Stim circuit for the same config.
2. Convert it to Qiskit.
3. Transpile against the selected IQM backend.
4. Record:
   - original depth,
   - transpiled depth,
   - two-qubit gate count,
   - SWAP count,
   - final layout.
5. Compare automatic layout vs custom 5x5 Emerald layout when available.

Gate-level acceptance criteria:

- No unsupported gates remain.
- Measurement count is unchanged.
- Circuit depth is explainable.
- SWAP count is either zero or explicitly documented.

Expected deliverable:

- A table comparing transpilation metrics for automatic vs custom layout.

### Phase 3: First Hardware Run

Purpose: get real raw data and a first hardware LER.

Steps:

1. Use a conservative shot count for first run.
2. Submit the transpiled circuit to IQM Resonance.
3. Save the job ID immediately.
4. Save raw counts and expanded measurement array.
5. Run syndrome extraction.
6. Decode with the same PyMatching path used in simulation.
7. Save LER, uncertainty, and detector diagnostics.

Hardware acceptance criteria:

- Returned shot count equals requested shot count.
- Raw measurement array width equals Stim measurement count.
- Detector firing rates are not all zero and not all near 0.5.
- Logical observable data exists.
- LER calculation uses decoded corrections, not just raw observable flip rate.

Expected deliverable:

- First hardware result summary:
  - backend,
  - shots,
  - circuit depth,
  - SWAP count,
  - mean syndrome weight,
  - LER plus uncertainty.

### Phase 4: Improve the Result

This phase is where judging points are most likely gained.

Priority order:

1. Custom Emerald mapping.
2. Calibration-aware noise model.
3. Calibration-weighted PyMatching.
4. Reset vs no-reset comparison.
5. Multiple patches on Emerald.
6. Multiple QPU comparison if practical.
7. Dynamical decoupling.
8. PulLA.
9. NVIDIA Ising.

For every improvement, keep the same comparison structure:

```text
baseline config -> improved config -> changed variable -> LER delta -> explanation
```

Do not mix too many changes in one result. The final story is stronger if each improvement has a clear reason.

### Phase 5: Final Documentation and Demo

The final submission should include a readable Markdown report, not only code.

Suggested report structure:

- Problem statement in simple language.
- Pipeline diagram.
- Exact MVP architecture.
- What we reused from the provided repo.
- What we implemented.
- Simulation baseline results.
- Hardware run results.
- Circuit/transpilation optimization evidence.
- Noise model and decoder explanation.
- What improved LER and what did not.
- Limitations and next steps.

Suggested demo:

- One command or notebook cell to run a simulation.
- One saved hardware result replay that does not require rerunning the QPU job.
- One plot/table showing LER.
- One plot/table showing detector firing rates or patch comparison.

Suggested 2-minute video:

- 20 seconds: what the challenge is.
- 30 seconds: architecture and why offline decoding works.
- 30 seconds: live or recorded run through the pipeline.
- 25 seconds: results and diagnostics.
- 15 seconds: advanced work, such as custom mapping, calibration, PulLA, or Ising.

### Definition of Done

MVP is done when:

- A distance-3 surface-code memory experiment runs end to end in simulation.
- The same circuit path can be transpiled for IQM hardware.
- At least one hardware result can be decoded offline.
- LER and uncertainty are computed from decoder output.
- Results are saved and summarized in Markdown.

Competitive version is done when:

- Custom mapping reduces or eliminates SWAP overhead.
- Simulation and hardware results are compared.
- Calibration data informs either the noise model or decoder weights.
- At least one improvement experiment is documented with before/after metrics.
- The final report is understandable to someone who did not read the code.

