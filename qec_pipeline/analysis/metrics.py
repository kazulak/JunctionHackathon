from __future__ import annotations

from math import sqrt


def binomial_standard_error(rate: float, shots: int) -> float:
    """Return 1-sigma binomial uncertainty for a logical failure rate."""
    if shots <= 0:
        raise ValueError("shots must be positive")
    return sqrt(rate * (1.0 - rate) / shots)
