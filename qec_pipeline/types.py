from __future__ import annotations

from pathlib import Path
from typing import Any

# Plain tuple results passed between pipeline steps.
#
# CircuitResult:
#   (stim_circuit, detector_model, measurement_order, circuit_info)
# RawResult:
#   (measurements, counts, raw_info)
# SyndromeResult:
#   (detection_events, observable_flips, syndrome_info)
# DecodeResult:
#   (predicted_observables, logical_failures, ler, uncertainty, decoder_info)
#
# The dictionaries are small metadata objects written to JSON for inspection.

CircuitResult = tuple[Any, Any, tuple[int, ...], dict[str, Any]]
RawResult = tuple[Any, dict[str, int] | None, dict[str, Any]]
SyndromeResult = tuple[Any, Any, dict[str, Any]]
DecodeResult = tuple[Any, Any, float, float, dict[str, Any]]
BasisRunResult = tuple[str, CircuitResult, RawResult, SyndromeResult, DecodeResult, dict[str, Any]]
PipelineResult = tuple[Path, list[BasisRunResult], list[str]]
