# Configs

```bash
python main.py <config>                                         # one run
python main.py --dry-run --print-config <config>                # show the plan, run nothing
python scripts/sweep_rounds.py <config> --rounds 1 7 4          # LER vs rounds (start stop count)
python scripts/sweep_rounds.py <config> --set code.mid_circuit_reset=feedforward   # override any key
```

| Config | Purpose |
| --- | --- |
| `hw_d3_noreset_dd_iqm.yaml` | **Hardware.** d3 on IQM Emerald: no mid-circuit reset, grouped readout, IQM dynamical decoupling, passive reset between shots, pinned patch QB13–QB45. Run `--preflight` first ([runbook](../docs/HARDWARE_RUNBOOK.md)). |
| `hw_d3_noreset_dd_sim.yaml` | Simulator twin of the hardware config (prediction). |
| `demo_stim_no_noise.yaml` | Noiseless smoke test; LER must be 0. |
| `sweep_d3_baseline_sim.yaml` | Reference d3 simulator with Qiskit-style reset every round and June calibration, plain calibrated MWPM. |
| `sweep_d3_decoder_kfold_sim.yaml` | Same circuit; decoder candidates (correlated matching, ensembles, gating) chosen by k-fold cross-validation. |
| `sweep_d3_postselected_sim.yaml` | Same circuit with low-syndrome postselection (diagnostic; discards shots). |
| `sim_iqm_emerald_surface_d5_calibrated.yaml` | d5 simulator on a routed Emerald layout (above threshold). |
| `calibration/emerald_<timestamp>.json` | IQM calibration dumps. Fetch a fresh one with `scripts/fetch_calibration.py`; the hardware preflight refuses a stale file. |

## YAML sections

```yaml
experiment: {name: my_run, description: "...", seed: 1}   # name = folder under results/

code:
  family: surface_code_iqm        # surface_code | surface_code_iqm | surface_code_unrotated
  distance: 3
  rounds: 1                       # overwritten by sweeps
  basis: both                     # memory_z | memory_x | both
  mid_circuit_reset: none         # reset (MR) | feedforward (M + conditional X) | none (two-round detectors)

backend:
  name: iqm_hardware              # or simulator (options: {seed: 1})
  shots: 2000
  options:
    quantum_computer: emerald
    optimization_level: 3
    batch_submit: true            # a sweep is one IQM job
    omit_initial_resets: true     # qubits start in |0> after IQM's reset between shots
    group_measurements: true      # adjacent readouts, so IQM multiplexes them
    dynamical_decoupling: true    # IQM native DD
    # active_reset_cycles: 2      # IQM active reset between shots; left 10-20 % init error in Oct 2026, keep off

noise:                            # simulator: injected noise; hardware: decoder's error model only
  model: iqm_calibration          # or no_noise | simple_depolarizing (parameters: {one_qubit_error: ..., ...})
  calibration_file: configs/calibration/emerald_2026-10-04T05_09_03Z.json
  options:
    two_qubit_scale: 1.5          # fitted to r = 1 hardware
    round_duration_s: 1.29e-6     # per reset strategy, from scripts/pulla_schedule_report.py
    idle_t2: echo                 # echo with DD, ramsey without
    # full list: docs/CALIBRATED_SIMULATION.md

decoder:
  name: pymatching_calibrated     # observable_rate | pymatching | pymatching_calibrated | pymatching_auto | pymatching_pij
  options: {}
  # pymatching_auto options: candidate_selection_mode (kfold default, holdout, current_batch = in-sample/optimistic),
  #   include_correlated_matching, include_matching_ensembles, gated_no_correction_quantiles,
  #   postselect_weight_quantile (reports LER on kept shots only)

mapping:
  strategy: calibration_best_patch   # none | calibration_best_patch (native d3) | calibration_routed_layout (d5)
  calibration_file: configs/calibration/emerald_2026-10-04T05_09_03Z.json
  options: {exclude_qubits: [QB9, QB25, QB41, QB46, QB47]}
  hardware_patch: {stim_to_hardware: {...}}   # pin a patch (scripts/select_patch.py)

artifacts: {root: results, save_raw_measurements: true, save_syndromes: true, save_report: true}
```
