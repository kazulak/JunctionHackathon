from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from qec_pipeline.analysis.reports import write_run_summary
from qec_pipeline.artifacts import prepare_run_directory
from qec_pipeline.backends.simulator import run_simulator_backend
from qec_pipeline.config import ExperimentConfig
from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.decoders.trivial_decoder import decode_trivial_no_noise
from qec_pipeline.syndromes import extract_detection_events
from qec_pipeline.types import PipelineState

StageFn = Callable[[PipelineState], PipelineState]


@dataclass(frozen=True)
class Stage:
    name: str
    description: str
    run: StageFn


def describe_pipeline(config: ExperimentConfig) -> list[str]:
    """Return human-readable stage names for dry runs and documentation."""
    return [stage.description for stage in build_stages(config)]


def run_pipeline(config: ExperimentConfig) -> PipelineState:
    """Run all configured stages.

    Input:
        config: fully loaded experiment config.

    Output:
        Final PipelineState containing artifacts and metrics.
    """
    state = PipelineState(config=config)
    for stage in build_stages(config):
        state = stage.run(state)
    return state


def build_stages(config: ExperimentConfig) -> list[Stage]:
    """Build the stage list from config.

    This is the orchestrator boundary. Keep it small: selection of code family,
    backend, decoder, and reporting should happen here or in a registry module.
    """
    return [
        Stage(
            name="prepare_artifacts",
            description=f"Prepare run directory under {config.artifacts.root}",
            run=_prepare_artifacts,
        ),
        Stage(
            name="generate_code",
            description=f"Generate {config.code.family} circuit",
            run=_generate_code,
        ),
        Stage(
            name="build_noise_model",
            description=f"Build {config.noise.model} noise model",
            run=_build_noise_model,
        ),
        Stage(
            name="map_or_transpile",
            description=f"Apply mapping strategy: {config.mapping.strategy}",
            run=_map_or_transpile,
        ),
        Stage(
            name="execute_backend",
            description=f"Run backend: {config.backend.name}",
            run=_execute_backend,
        ),
        Stage(
            name="extract_syndromes",
            description="Extract detector events and observable flips",
            run=_extract_syndromes,
        ),
        Stage(
            name="decode",
            description=f"Decode with {config.decoder.name}",
            run=_decode,
        ),
        Stage(
            name="report",
            description="Write metrics and concise Markdown report",
            run=_write_report,
        ),
    ]


def _prepare_artifacts(state: PipelineState) -> PipelineState:
    return prepare_run_directory(state).add_note("Prepared run directory.")


def _generate_code(state: PipelineState) -> PipelineState:
    config = state.config
    if config.code.family != "surface_code":
        raise NotImplementedError(f"{config.code.family} code generation")
    circuit = build_surface_code_circuit(config.code, config.noise)
    return state.with_updates(circuit=circuit).add_note("Generated toy surface-code circuit.")


def _build_noise_model(state: PipelineState) -> PipelineState:
    if state.config.noise.model not in {"none", "no_noise"}:
        raise NotImplementedError(f"{state.config.noise.model} noise model")
    return state.add_note("No noise model applied.")


def _map_or_transpile(state: PipelineState) -> PipelineState:
    if state.config.mapping.strategy != "none":
        raise NotImplementedError(f"{state.config.mapping.strategy} mapping")
    return state.add_note("No mapping/transpilation needed for toy simulator.")


def _execute_backend(state: PipelineState) -> PipelineState:
    if state.circuit is None:
        raise ValueError("Cannot run backend before circuit generation.")
    if state.config.backend.name != "simulator":
        raise NotImplementedError(f"{state.config.backend.name} backend")
    raw = run_simulator_backend(state.config.backend, state.circuit)
    return state.with_updates(raw_measurements=raw).add_note("Ran deterministic no-noise simulator.")


def _extract_syndromes(state: PipelineState) -> PipelineState:
    if state.circuit is None or state.raw_measurements is None:
        raise ValueError("Cannot extract syndromes before circuit and measurements exist.")
    syndromes = extract_detection_events(state.circuit, state.raw_measurements)
    return state.with_updates(syndromes=syndromes).add_note("Extracted zero detection events.")


def _decode(state: PipelineState) -> PipelineState:
    if state.circuit is None or state.syndromes is None:
        raise ValueError("Cannot decode before circuit and syndromes exist.")
    if state.config.decoder.name != "trivial":
        raise NotImplementedError(f"{state.config.decoder.name} decoder")
    result = decode_trivial_no_noise(state.config.decoder, state.circuit, state.syndromes)
    metrics = {
        **state.metrics,
        "ler": result.ler,
        "uncertainty": result.uncertainty,
        "logical_failures": result.metadata["logical_failures"],
        "shots": result.metadata["shots"],
    }
    return state.with_updates(decoder_result=result, metrics=metrics).add_note(
        "Decoded with trivial no-noise decoder."
    )


def _write_report(state: PipelineState) -> PipelineState:
    if state.run_dir is None:
        raise ValueError("Cannot write report before run directory exists.")
    write_run_summary(state, state.run_dir / "summary.md")
    return state.add_note("Wrote summary report.")
