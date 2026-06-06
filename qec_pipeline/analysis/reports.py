from __future__ import annotations

from pathlib import Path

from qec_pipeline.types import PipelineState


def write_run_summary(state: PipelineState, output_path: Path) -> None:
    """Write a concise Markdown summary for one run.

    Input:
        state: final PipelineState with config, metrics, decoder result, and notes.
        output_path: path to `summary.md`.

    Output:
        Markdown file containing the experiment settings and key metrics.
    """
    config = state.config
    result = state.decoder_result

    lines = [
        f"# Run Summary: {config.experiment.name}",
        "",
        "## Config",
        "",
        f"- Code: {config.code.family}, d={config.code.distance}, rounds={config.code.rounds}",
        f"- Basis/reset: {config.code.basis}/{config.code.reset_mode}",
        f"- Backend: {config.backend.name}, shots={config.backend.shots}",
        f"- Noise: {config.noise.model}",
        f"- Decoder: {config.decoder.name}",
        f"- Mapping: {config.mapping.strategy}",
        "",
        "## Result",
        "",
    ]

    if result is None:
        lines.append("- Decoder result: missing")
    else:
        lines.extend(
            [
                f"- LER: {result.ler}",
                f"- Uncertainty: {result.uncertainty}",
                f"- Logical failures: {result.metadata.get('logical_failures')}",
            ]
        )

    if state.circuit is not None:
        lines.extend(
            [
                "",
                "## Circuit",
                "",
                f"- Qubits: {state.circuit.metadata.get('num_qubits')}",
                f"- Measurements: {state.circuit.metadata.get('num_measurements')}",
                f"- Detectors: {state.circuit.metadata.get('num_detectors')}",
                f"- Observables: {state.circuit.metadata.get('num_observables')}",
            ]
        )

    if state.notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in state.notes)

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
