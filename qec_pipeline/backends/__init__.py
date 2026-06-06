from __future__ import annotations

from typing import Any, Callable

from qec_pipeline.backends.iqm_hardware import run_iqm_hardware_backend
from qec_pipeline.backends.simulator import run_simulator_backend


BackendRunner = Callable[[dict[str, Any], tuple, dict[str, Any]], tuple]


BACKENDS: dict[str, BackendRunner] = {
    "simulator": run_simulator_backend,
    "iqm_hardware": run_iqm_hardware_backend,
}


def get_backend_runner(name: str) -> BackendRunner:
    try:
        return BACKENDS[name]
    except KeyError as exc:
        available = ", ".join(sorted(BACKENDS))
        raise ValueError(f"Unknown backend: {name}. Available: {available}") from exc
