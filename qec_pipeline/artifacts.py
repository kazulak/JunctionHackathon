"""Result directories: where runs are written, and reading saved runs back.

Layout: a single run is `results/<experiment>/<timestamp>/<basis>/`; a sweep is
`results/<experiment>_rounds_sweep/<timestamp>/runs/<experiment>_rounds_<r>/<timestamp>/<basis>/`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import stim


def utc_timestamp() -> str:
    """Return a UTC timestamp for result directory names.

    Microseconds are included so two runs started in the same second do not collide.
    """
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")


def prepare_run_directory(config: dict[str, Any]) -> Path:
    """Create `results/<experiment>/<timestamp>` and return the path."""
    root = Path(config["artifacts"].get("root", "results"))
    run_dir = root / config["experiment"]["name"] / utc_timestamp()
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def sweep_basis_dirs(sweep_dir: Path) -> list[Path]:
    """Every per-basis run directory of a finished sweep."""
    return sorted(Path(sweep_dir).glob("runs/*/*/memory_*"))


def load_basis_run(basis_dir: Path) -> dict[str, Any]:
    """Read one saved basis run: its circuit, raw measurements (if saved), and metadata."""
    basis_dir = Path(basis_dir)
    measurements_path = basis_dir / "raw_measurements.npz"
    return {
        "circuit": stim.Circuit.from_file(basis_dir / "circuit.stim"),
        "measurements": (
            np.load(measurements_path)["measurements"].astype(bool) if measurements_path.exists() else None
        ),
        "circuit_info": _read_json(basis_dir / "circuit_metadata.json"),
        "raw_info": _read_json(basis_dir / "raw_metadata.json"),
        "metrics": _read_json(basis_dir / "metrics.json"),
    }


def find_stim_circuits(path: Path) -> list[Path]:
    """`circuit.stim` files under a run, basis, or experiment directory (latest run), or the file itself."""
    if path.is_file() and path.name == "circuit.stim":
        return [path]
    if path.is_dir() and (path / "circuit.stim").exists():
        return [path / "circuit.stim"]
    if path.is_dir():
        basis_circuits = sorted(path.glob("*/circuit.stim"))
        if basis_circuits:
            return basis_circuits
        child_dirs = sorted(child for child in path.iterdir() if child.is_dir())
        if child_dirs:
            return sorted(child_dirs[-1].glob("*/circuit.stim"))
    return []


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
