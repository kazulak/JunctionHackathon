"""Shared statistics for logical error rates.

Single source for binomial uncertainties, per-round conversion, and per-round fits,
so the pipeline, sweeps, and comparison scripts report the same numbers.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

import numpy as np
from scipy.optimize import minimize

_EPS_BOUNDS = (1e-9, 0.5 - 1e-9)
# A > 1 is allowed: the first round has fewer error locations (time boundary), which
# Google handles by fitting only from round 3 (arXiv:2207.06431, Suppl. XIII).
_AMPLITUDE_BOUNDS = (1e-6, 2.0)


def binomial_standard_error(rate: float, shots: int) -> float:
    """Return 1-sigma binomial uncertainty for a logical failure rate."""
    if shots <= 0:
        raise ValueError("shots must be positive")
    return sqrt(rate * (1.0 - rate) / shots)


def wilson_interval(failures: int, shots: int, z: float = 1.0) -> tuple[float, float]:
    """Return the Wilson score interval for a binomial rate (z=1 gives ~68%).

    Unlike the plain standard error, the interval stays non-degenerate at 0 or
    `shots` failures, so "0 observed failures" is reported with a real upper bound.
    """
    if shots <= 0:
        raise ValueError("shots must be positive")
    rate = failures / shots
    denominator = 1.0 + z * z / shots
    center = (rate + z * z / (2 * shots)) / denominator
    half_width = z * sqrt(rate * (1.0 - rate) / shots + z * z / (4 * shots * shots)) / denominator
    return max(0.0, center - half_width), min(1.0, center + half_width)


def per_round_ler(total_ler: float, total_uncertainty: float, rounds: int) -> tuple[float, float]:
    """Convert a total memory-failure probability to a per-round probability.

    Uses P(r) = (1 - (1 - 2e)^r) / 2 and first-order error propagation.
    """
    if rounds <= 1:
        return float(total_ler), float(total_uncertainty)
    clamped = min(max(float(total_ler), 0.0), 0.499999999)
    survival = 1.0 - 2.0 * clamped
    per_round = (1.0 - survival ** (1.0 / rounds)) / 2.0
    derivative = (1.0 / rounds) * survival ** ((1.0 / rounds) - 1.0)
    return float(per_round), float(abs(derivative) * total_uncertainty)


def is_postselected(row: dict[str, Any]) -> bool:
    """True when a result row kept only part of its shots."""
    fraction = row.get("postselection_fraction")
    if fraction in {None, ""}:
        return False
    return float(fraction) < 1.0


def fit_per_round_error(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fit P(r) = (1 - A (1 - 2e)^r) / 2 to binomial counts by maximum likelihood.

    `rows` need `rounds`, `logical_failures`, and `shots`. The amplitude A absorbs
    state-preparation, final-readout, and first-round boundary effects, as in Google's
    surface-code analysis.
    Postselected rows are excluded because their kept fraction changes with r.

    Returns the fitted error per round, its 1-sigma uncertainty (inverse Hessian),
    the amplitude, and which rows were excluded and why.
    """
    used, excluded = [], []
    for row in rows:
        if is_postselected(row):
            excluded.append({"rounds": int(row["rounds"]), "reason": "postselected"})
            continue
        if int(row.get("shots") or 0) <= 0:
            excluded.append({"rounds": int(row["rounds"]), "reason": "no shots"})
            continue
        used.append(row)

    result: dict[str, Any] = {
        "fit_points": len(used),
        "fitted_logical_error_per_round": None,
        "fitted_logical_error_per_round_uncertainty": None,
        "fit_amplitude": None,
        "fit_method": "binomial_mle",
        "note": None,
        "excluded_points": excluded,
    }
    distinct_rounds = {int(row["rounds"]) for row in used}
    if len(distinct_rounds) < 2:
        result["note"] = "need at least two distinct round values"
        return result

    rounds = np.array([float(row["rounds"]) for row in used])
    failures = np.array([float(row["logical_failures"]) for row in used])
    shots = np.array([float(row["shots"]) for row in used])

    def negative_log_likelihood(params: np.ndarray) -> float:
        error, amplitude = params
        probability = 0.5 * (1.0 - amplitude * (1.0 - 2.0 * error) ** rounds)
        probability = np.clip(probability, 1e-12, 1.0 - 1e-12)
        return float(-(failures * np.log(probability) + (shots - failures) * np.log1p(-probability)).sum())

    start = np.array([_initial_error_guess(rounds, failures / shots), 0.95])
    optimum = minimize(
        negative_log_likelihood,
        start,
        method="L-BFGS-B",
        bounds=[_EPS_BOUNDS, _AMPLITUDE_BOUNDS],
    )
    error, amplitude = (float(value) for value in optimum.x)
    result["fitted_logical_error_per_round"] = error
    result["fit_amplitude"] = amplitude
    result["fitted_logical_error_per_round_uncertainty"] = _error_uncertainty(
        negative_log_likelihood, optimum.x
    )
    return result


def _initial_error_guess(rounds: np.ndarray, rates: np.ndarray) -> float:
    survival = np.clip(1.0 - 2.0 * rates, 1e-6, 1.0)
    if np.ptp(rounds) == 0:
        return 0.01
    slope = np.polyfit(rounds, np.log(survival), 1)[0]
    guess = (1.0 - np.exp(min(slope, 0.0))) / 2.0
    return float(np.clip(guess, 1e-6, 0.49))


def _error_uncertainty(function, params: np.ndarray) -> float | None:
    """1-sigma uncertainty on the error parameter from a numeric Hessian."""
    steps = np.maximum(np.abs(params) * 1e-4, 1e-7)
    hessian = np.zeros((2, 2))
    for i in range(2):
        for j in range(2):
            shift_i = np.eye(2)[i] * steps[i]
            shift_j = np.eye(2)[j] * steps[j]
            hessian[i, j] = (
                function(params + shift_i + shift_j)
                - function(params + shift_i - shift_j)
                - function(params - shift_i + shift_j)
                + function(params - shift_i - shift_j)
            ) / (4.0 * steps[i] * steps[j])
    if params[1] >= _AMPLITUDE_BOUNDS[1] - 1e-9:
        # Amplitude pinned at its bound: treat it as fixed and use the 1-D curvature.
        return float(1.0 / sqrt(hessian[0, 0])) if hessian[0, 0] > 0 else None
    try:
        covariance = np.linalg.inv(hessian)
    except np.linalg.LinAlgError:
        return None
    variance = covariance[0, 0]
    return float(sqrt(variance)) if variance > 0 and np.isfinite(variance) else None

