# -*- coding: utf-8 -*-

from internal_helpers import *

"""
surface_code_stim.py

Full pipeline: (Stim circuit →) Qiskit → IQM Emerald → Decoder

  ┌─────────────────────────────────────────────────────────────────────┐
  │  Code: rotated surface code, memory-Z experiment                    │
  │  Distance 3: 9 data + 8 ancilla = 17 qubits                         │
  │  Connectivity: diagonal,                                            │
  │  SWAPs for 6 of the 12 unique CX pairs. Circuit depth ≈ 9 (ideal).  │
  └─────────────────────────────────────────────────────────────────────┘

Sections
--------
  1. Stim circuit generation
  2. Stim → Qiskit conversion
  3. OPTIONAL Emerald qubit mapping
  4. Stim simulation  (no hardware, for threshold / LER curves)
  5. Hardware execution on IQM Resonance
  6. Hardware results → detection events → Decoder

Usage
-----
  # Simulation only:
  from surface_code_stim import simulate_ler

  # Full hardware pipeline:
  from surface_code_stim import run_hardware_experiment


"""

import numpy as np
import stim
import pymatching
from qiskit import QuantumCircuit, transpile
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
#  1.  STIM CIRCUIT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

#: Default noise model matching IQM Emerald typical gate error rates (~0.1-0.5%).
#: Adjust these based on your latest calibration data from Resonance.
DEFAULT_NOISE = dict(
    after_clifford_depolarization  = 0.003,
    after_reset_flip_probability   = 0.003,
    before_measure_flip_probability= 0.003,
    before_round_data_depolarization = 0.003,
)


def make_stim_circuit(
    distance: int = 3,
    rounds: int = 1,
    noise: Optional[dict] = None,
    basis: str = "Z",
) -> stim.Circuit:
    """
    Generates a Stim circuit for the rotated surface code (memory experiment).

    Uses Stim's reference generator, so detectors and the logical observable are
    guaranteed correct. Pass noise=None for the noiseless circuit we execute on
    hardware (the chip supplies the noise); pass noise=DEFAULT_NOISE to build the
    detector-error-model circuit used by syndrome extraction / the decoder.

    Parameters
    ----------
    distance : code distance (3 -> 17 qubits, fits a 5x5 Emerald patch)
    rounds   : number of stabilizer-measurement rounds
    noise    : None or a dict like DEFAULT_NOISE (uniform depolarizing model)
    basis    : "Z" (catches X errors) or "X" (catches Z errors)

    Returns
    -------
    stim.Circuit
    """
    n = noise or {}
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis.lower()}",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=n.get("after_clifford_depolarization", 0.0),
        after_reset_flip_probability=n.get("after_reset_flip_probability", 0.0),
        before_measure_flip_probability=n.get("before_measure_flip_probability", 0.0),
        before_round_data_depolarization=n.get("before_round_data_depolarization", 0.0),
    )

def get_circuit_info(circuit: stim.Circuit) -> dict:
    """
    Returns a summary dict of qubit counts and measurement structure.
    Useful for sanity-checking before hardware runs.
    """
    data_q, anc_q = get_qubit_lists(circuit)
    return {
        "num_qubits"      : circuit.num_qubits,
        "num_data_qubits" : len(data_q),
        "num_anc_qubits"  : len(anc_q),
        "num_measurements": circuit.num_measurements,
        "num_detectors"   : circuit.num_detectors,
        "num_observables" : circuit.num_observables,
        "data_stim_indices": sorted(data_q),
        "anc_stim_indices" : sorted(anc_q),
        "meas_order"      : get_meas_order(circuit),
    }


def make_qiskit_circuit(
    distance: int = 3,
    rounds: int = 1,
    basis: str = "Z",
):
    """
    Generates a Qiskit circuit for the rotated surface code by building the
    noiseless Stim circuit and converting it (see stim_to_qiskit below).

    Returns
    -------
    qiskit.QuantumCircuit
    """
    qc, _stim_to_dense, _meas_order = stim_to_qiskit(
        make_stim_circuit(distance, rounds, noise=None, basis=basis)
    )
    return qc

# ─────────────────────────────────────────────────────────────────────────────
#  2.  STIM → QISKIT CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

# Instructions that exist only in Stim's simulation model — skip them when
# building the Qiskit circuit for hardware.
_STIM_SKIP = frozenset({
    "DEPOLARIZE1", "DEPOLARIZE2", "X_ERROR", "Z_ERROR", "Y_ERROR",
    "PAULI_CHANNEL_1", "PAULI_CHANNEL_2", "CORRELATED_ERROR",
    "ELSE_CORRELATED_ERROR", "DETECTOR", "OBSERVABLE_INCLUDE",
    "QUBIT_COORDS", "SHIFT_COORDS", "TICK",
})


def stim_to_qiskit(stim_circuit: stim.Circuit) -> tuple[QuantumCircuit, dict, list]:
    """
    Converts a (noiseless) Stim circuit into a Qiskit QuantumCircuit.

    The Stim circuit is first flattened to unroll any REPEAT blocks,
    then noise/annotation instructions are dropped. The resulting
    Qiskit circuit is suitable for transpilation onto IQM Resonance.

    Parameters
    ----------
    stim_circuit : stim.Circuit  (use make_stim_circuit(..., noise=None))

    Returns
    -------
    qc            : QuantumCircuit  with dense qubit indices 0..N-1
    stim_to_dense : dict  stim_qubit_index → dense_qiskit_index
    meas_order    : list[int]  stim qubit indices in measurement order
                    Use this to map hardware bitstrings back to Stim's
                    measurement record for detection event conversion.
    """
    flat = stim_circuit.flattened()

    # Build dense re-indexing: Stim uses sparse indices (e.g. 1,3,5,8,…,25)
    # Qiskit needs contiguous 0..N-1 indices.
    data_q, anc_q = get_qubit_lists(stim_circuit)
    all_stim_q    = sorted(set(data_q + anc_q))
    stim_to_dense = {sq: i for i, sq in enumerate(all_stim_q)}

    n_qubits = len(all_stim_q)
    n_clbits = stim_circuit.num_measurements # one classical bit per measured qubit
    qc = QuantumCircuit(n_qubits, n_clbits)

    meas_idx  = 0
    meas_order = []

    for instr in flat:
        name = instr.name

        if name in _STIM_SKIP:
            continue

        # Extract qubit targets (ignore measurement-record targets in M gates)
        targets = [t.value for t in instr.targets_copy() if t.is_qubit_target]
        dense   = [stim_to_dense[t] for t in targets]

        if name == "R":
            for d in dense:
                qc.reset(d)

        elif name == "H":
            for d in dense:
                qc.h(d)

        elif name == "CX":
            for i in range(0, len(dense), 2):
                qc.cx(dense[i], dense[i + 1])

        elif name == "CZ":
            for i in range(0, len(dense), 2):
                qc.cz(dense[i], dense[i + 1])

        elif name == "X":
            for d in dense:
                qc.x(d)

        elif name in ("M", "MR"):
            for stim_q, d in zip(targets, dense):
                qc.measure(d, meas_idx)
                meas_order.append(stim_q)
                meas_idx += 1
            # MR = measure-then-reset (mid-circuit reset for multi-round)
            if name == "MR":
                for d in dense:
                    qc.reset(d)

        else:
            # Warn about genuinely unhandled gates (not noise/annotations)
            raise NotImplementedError(
                f"[stim_to_qiskit] Unhandled gate '{name}'. "
                f"If this is a noise/annotation instruction, add it to _STIM_SKIP. "
                f"If it is a gate instruction, implement it explicitly."
                )

    return qc, stim_to_dense, meas_order


# ─────────────────────────────────────────────────────────────────────────────
#  3.  EMERALD QUBIT MAPPING  (see build_emerald_qubit_rotated.py, calibration_layout.py)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
#  4.  STIM SIMULATION  (no hardware needed)  -> pipeline baseline
# ─────────────────────────────────────────────────────────────────────────────

def simulate_ler(distance: int = 3, rounds: int = 1, basis: str = "Z",
                 noise: Optional[dict] = None, shots: int = 200_000):
    """
    Pure-Stim baseline: sample detectors from the noisy circuit, decode with MWPM,
    return (ler, err). Run this BEFORE spending QPU time to validate the pipeline.
    noise=None reproduces the non-negotiable check: ler MUST be exactly 0.
    """
    circ = make_stim_circuit(distance, rounds, noise=noise, basis=basis)
    det, obs = circ.compile_detector_sampler().sample(shots, separate_observables=True)
    matching = pymatching.Matching.from_detector_error_model(
        circ.detector_error_model(decompose_errors=True))
    pred = matching.decode_batch(det)
    fails = int(np.sum(np.any(pred != obs, axis=1)))
    ler = fails / shots
    return ler, float(np.sqrt(max(ler * (1 - ler), 0.0) / shots))

# ─────────────────────────────────────────────────────────────────────────────
#  5.  Hardware execution  (see run_on_hardware.py)
#  6.  Offline decoding   (see run_on_hardware.decode_hardware_results)
# ─────────────────────────────────────────────────────────────────────────────