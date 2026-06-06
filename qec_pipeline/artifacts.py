from __future__ import annotations

from datetime import datetime
from pathlib import Path

from qec_pipeline.config import ExperimentConfig
from qec_pipeline.types import PipelineState


def prepare_run_directory(state: PipelineState) -> PipelineState:
    """Create the output directory for one experiment run.

    Input:
        PipelineState with ExperimentConfig.

    Output:
        PipelineState with run_dir set.
    """
    config: ExperimentConfig = state.config
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = config.artifacts.root / config.experiment.name / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)
    return state.with_updates(run_dir=run_dir)
