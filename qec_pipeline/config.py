from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_experiment_config(path: Path) -> dict[str, Any]:
    """Load a YAML config as a normal dictionary."""
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    config["_config_path"] = str(path)
    _validate_minimum_config(config)
    return config


def config_summary(config: dict[str, Any]) -> str:
    experiment = config["experiment"]
    code = config["code"]
    backend = config["backend"]
    noise = config["noise"]
    decoder = config["decoder"]
    mapping = config["mapping"]

    return "\n".join(
        [
            f"name: {experiment['name']}",
            f"code: {code['family']} d={code['distance']} rounds={code['rounds']}",
            f"basis/reset: {code['basis']}/{code['reset_mode']}",
            f"backend: {backend['name']} shots={backend['shots']}",
            f"noise: {noise['model']}",
            f"decoder: {decoder['name']}",
            f"mapping: {mapping['strategy']}",
        ]
    )


def _validate_minimum_config(config: dict[str, Any]) -> None:
    required_sections = ["experiment", "code", "backend", "noise", "decoder", "mapping", "artifacts"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing config section: {section}")
