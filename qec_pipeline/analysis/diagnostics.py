from __future__ import annotations

from typing import Any

import numpy as np


def build_run_diagnostics(
    circuit_info: dict[str, Any],
    raw_info: dict[str, Any],
    syndrome_info: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build simple correctness/quality diagnostics for one basis run."""
    detector_firing_rate = np.asarray(
        syndrome_info.get("detector_firing_rate", []),
        dtype=float,
    )
    num_detectors = int(syndrome_info.get("num_detectors", len(detector_firing_rate)))
    warnings = []

    mean_detector_firing_rate = _safe_mean(detector_firing_rate)
    saturated_detector_count = int(
        ((0.4 <= detector_firing_rate) & (detector_firing_rate <= 0.6)).sum()
    )
    hot_detector_count = int((detector_firing_rate >= 0.25).sum())
    saturated_detector_fraction = (
        saturated_detector_count / num_detectors if num_detectors else 0.0
    )

    ler = float(metrics.get("ler", 0.0))
    if ler >= 0.45:
        warnings.append("LER is near 0.5; decoding is saturated or measurements are randomized.")
    if mean_detector_firing_rate >= 0.25:
        warnings.append("Mean detector firing rate is high; detector data may be near random.")
    if saturated_detector_fraction >= 0.5:
        warnings.append("Most detectors fire near 0.5; check circuit depth, mapping, and bit order.")

    qiskit_depth = raw_info.get("qiskit_depth")
    transpiled_depth = raw_info.get("transpiled_depth")
    depth_ratio = None
    if qiskit_depth and transpiled_depth:
        depth_ratio = float(transpiled_depth) / float(qiskit_depth)
        if depth_ratio >= 5.0:
            warnings.append(
                f"Transpiled depth is {depth_ratio:.1f}x Qiskit depth; routing is likely too costly."
            )
    if transpiled_depth and int(transpiled_depth) >= 200:
        warnings.append("Transpiled circuit depth is very high for a noisy QPU.")

    transpiled_ops = raw_info.get("transpiled_ops", {})
    two_qubit_ops = int(transpiled_ops.get("cz", 0)) + int(transpiled_ops.get("cx", 0))
    if two_qubit_ops >= 500:
        warnings.append("Transpiled circuit contains many two-qubit gates; expect poor LER.")

    return {
        "basis": metrics.get("basis"),
        "ler": ler,
        "uncertainty": metrics.get("uncertainty"),
        "num_detectors": num_detectors,
        "mean_detector_firing_rate": mean_detector_firing_rate,
        "hot_detector_count": hot_detector_count,
        "saturated_detector_count": saturated_detector_count,
        "saturated_detector_fraction": saturated_detector_fraction,
        "mean_syndrome_weight": syndrome_info.get("mean_syndrome_weight"),
        "observable_flip_rate": syndrome_info.get("observable_flip_rate"),
        "qiskit_depth": qiskit_depth,
        "transpiled_depth": transpiled_depth,
        "transpiled_depth_ratio": depth_ratio,
        "two_qubit_ops_after_transpile": two_qubit_ops,
        "num_measurements": circuit_info.get("num_measurements"),
        "num_qubits": circuit_info.get("num_qubits"),
        "warnings": warnings,
    }


def _safe_mean(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(values.mean())
