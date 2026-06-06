from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{name}' must be a mapping.")
    return value


@dataclass(frozen=True)
class ExperimentInfo:
    name: str
    description: str = ""
    seed: int | None = None


@dataclass(frozen=True)
class CodeConfig:
    family: str
    distance: int
    rounds: int
    basis: str
    reset_mode: str


@dataclass(frozen=True)
class BackendConfig:
    name: str
    shots: int
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NoiseConfig:
    model: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecoderConfig:
    name: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MappingConfig:
    strategy: str
    hardware_patch: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactConfig:
    root: Path
    save_raw_measurements: bool = True
    save_syndromes: bool = True
    save_report: bool = True


@dataclass(frozen=True)
class ExperimentConfig:
    path: Path
    experiment: ExperimentInfo
    code: CodeConfig
    backend: BackendConfig
    noise: NoiseConfig
    decoder: DecoderConfig
    mapping: MappingConfig
    artifacts: ArtifactConfig
    raw: dict[str, Any]

    def summary(self) -> str:
        return "\n".join(
            [
                f"name: {self.experiment.name}",
                f"code: {self.code.family} d={self.code.distance} rounds={self.code.rounds}",
                f"basis/reset: {self.code.basis}/{self.code.reset_mode}",
                f"backend: {self.backend.name} shots={self.backend.shots}",
                f"noise: {self.noise.model}",
                f"decoder: {self.decoder.name}",
                f"mapping: {self.mapping.strategy}",
            ]
        )


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load one YAML experiment config.

    Input:
        path: YAML file path.

    Output:
        ExperimentConfig with typed top-level sections and preserved raw data.
    """
    data = _load_yaml_mapping(path)

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    experiment = _section(data, "experiment")
    code = _section(data, "code")
    backend = _section(data, "backend")
    noise = _section(data, "noise")
    decoder = _section(data, "decoder")
    mapping = _section(data, "mapping")
    artifacts = _section(data, "artifacts")

    return ExperimentConfig(
        path=path,
        experiment=ExperimentInfo(
            name=str(experiment["name"]),
            description=str(experiment.get("description", "")),
            seed=experiment.get("seed"),
        ),
        code=CodeConfig(
            family=str(code["family"]),
            distance=int(code["distance"]),
            rounds=int(code["rounds"]),
            basis=str(code["basis"]),
            reset_mode=str(code["reset_mode"]),
        ),
        backend=BackendConfig(
            name=str(backend["name"]),
            shots=int(backend["shots"]),
            options=dict(backend.get("options", {})),
        ),
        noise=NoiseConfig(
            model=str(noise["model"]),
            parameters=dict(noise.get("parameters", {})),
        ),
        decoder=DecoderConfig(
            name=str(decoder["name"]),
            options=dict(decoder.get("options", {})),
        ),
        mapping=MappingConfig(
            strategy=str(mapping["strategy"]),
            hardware_patch=mapping.get("hardware_patch"),
            options=dict(mapping.get("options", {})),
        ),
        artifacts=ArtifactConfig(
            root=Path(artifacts.get("root", "results")),
            save_raw_measurements=bool(artifacts.get("save_raw_measurements", True)),
            save_syndromes=bool(artifacts.get("save_syndromes", True)),
            save_report=bool(artifacts.get("save_report", True)),
        ),
        raw=data,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load YAML with PyYAML, falling back to a minimal mapping parser.

    The fallback exists so `python main.py --dry-run` works before installing
    dependencies. Install PyYAML for full YAML support and matrix configs.
    """
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return _load_simple_mapping_yaml(path)

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return loaded


def _load_simple_mapping_yaml(path: Path) -> dict[str, Any]:
    """Parse the simple nested mapping style used by baseline configs.

    This intentionally does not implement the full YAML spec. It supports
    nested dictionaries, strings, ints, floats, booleans, and null values.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if stripped.startswith("- "):
            raise ValueError(
                f"Config {path}:{line_number} needs PyYAML for list syntax. "
                "Install requirements.txt to use this file."
            )

        key, separator, value = stripped.partition(":")
        if not separator:
            raise ValueError(f"Invalid config line {path}:{line_number}: {raw_line}")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        key = key.strip()
        value = value.strip()
        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)

    return root


def _parse_scalar(value: str) -> Any:
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value in {"null", "None", "~"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
