from __future__ import annotations

import re
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
            f"basis: {code['basis']}, mid-circuit reset: {code.get('mid_circuit_reset', 'reset')}",
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
    if "reset_mode" in config["code"]:
        raise ValueError("code.reset_mode was removed; use code.mid_circuit_reset (reset | feedforward | none)")


def apply_overrides(config: dict[str, Any], items: list[str], rename: bool = True) -> dict[str, Any]:
    """Apply command-line overrides `dotted.key=value` (value parsed as YAML) in place.

    With `rename`, each override is appended to `experiment.name` (`__key=value`, made
    filesystem-safe) so results of different variants never share a folder.
    """
    for item in items:
        if "=" not in item:
            raise ValueError(f"override must look like dotted.key=value, got {item!r}")
        key, raw_value = item.split("=", 1)
        *parents, leaf = key.split(".")
        node = config
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = yaml.safe_load(raw_value)
        if rename and parents[:1] != ["experiment"]:
            label = re.sub(r"[^A-Za-z0-9._=-]+", "_", f"{leaf}={raw_value}").strip("_")[:48]
            config["experiment"]["name"] = f"{config['experiment']['name']}__{label}"
    return config
