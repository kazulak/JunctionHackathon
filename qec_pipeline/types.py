from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CircuitBundle:
    """Circuit artifacts passed between code generation, mapping, and backends.

    source_circuit:
        Canonical circuit. For MVP this should be a Stim circuit.
    hardware_circuit:
        Backend-ready circuit. For IQM this should be a Qiskit circuit.
    detector_model:
        Decoder graph source, usually a Stim detector error model.
    measurement_order:
        Mapping from backend classical bits to source-circuit measurement record.
    metadata:
        Counts, depths, gate counts, qubit coordinates, or layout diagnostics.
    """

    source_circuit: Any | None = None
    hardware_circuit: Any | None = None
    detector_model: Any | None = None
    measurement_order: tuple[int, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawMeasurementBundle:
    """Raw shot data returned by simulator or hardware backend."""

    measurements: Any
    counts: dict[str, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyndromeBundle:
    """Syndromes consumed by decoders."""

    detection_events: Any
    observable_flips: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecoderResult:
    """Decoder output used for LER analysis."""

    predicted_observables: Any
    logical_failures: Any
    ler: float
    uncertainty: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineState:
    """Immutable pipeline state.

    Stage functions should return a new PipelineState instead of mutating the
    input state. This keeps the orchestration easy to test and reason about.
    """

    config: Any
    run_dir: Path | None = None
    circuit: CircuitBundle | None = None
    raw_measurements: RawMeasurementBundle | None = None
    syndromes: SyndromeBundle | None = None
    decoder_result: DecoderResult | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def with_updates(self, **updates: Any) -> PipelineState:
        return replace(self, **updates)

    def add_note(self, note: str) -> PipelineState:
        return replace(self, notes=(*self.notes, note))
