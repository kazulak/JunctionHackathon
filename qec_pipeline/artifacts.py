from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
