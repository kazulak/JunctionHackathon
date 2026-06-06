from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def prepare_run_directory(config: dict[str, Any]) -> Path:
    """Create `results/<experiment>/<timestamp>` and return the path."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    root = Path(config["artifacts"].get("root", "results"))
    run_dir = root / config["experiment"]["name"] / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir
