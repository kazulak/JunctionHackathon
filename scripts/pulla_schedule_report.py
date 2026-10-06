"""Compile pipeline circuits against the live IQM calibration WITHOUT running them.

Uses IQM Pulla (pulse-level compiler) through the Resonance API with the token in `.env`.
Nothing is executed on the QPU, so no credits are spent. Reports, per circuit:

- the compiled schedule duration and the per-shot time (schedule + end delay),
- the extra time each additional syndrome round costs,
- which IQM gate implementations were used (e.g. `reset_conditional`, `measure`),
- estimated QPU seconds for a given number of shots.

Examples:

    python scripts/pulla_schedule_report.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 5 7 --dd --shots 2000
    python scripts/pulla_schedule_report.py configs/hw_d3_noreset_dd_iqm.yaml --rounds 1 3 \\
        --mid-circuit-reset reset   # June-style Qiskit resets, for comparison
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.backends.iqm_hardware import _load_dotenv, _prepare_iqm_request
from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.codes import get_code_builder
from qec_pipeline.config import load_experiment_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    parser.add_argument("--rounds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--basis", default="memory_z", choices=["memory_z", "memory_x"])
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override backend.options, e.g. group_measurements=false.",
    )
    parser.add_argument(
        "--mid-circuit-reset",
        choices=["reset", "feedforward", "none"],
        default=None,
        help="Override code.mid_circuit_reset.",
    )
    parser.add_argument("--active-reset-cycles", type=int, default=None, help="IQM active reset between shots.")
    parser.add_argument("--dd", action="store_true", help="Enable IQM's standard dynamical decoupling.")
    parser.add_argument("--shots", type=int, default=2000, help="Shots per circuit for the QPU-time estimate.")
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    if args.mid_circuit_reset:
        config["code"]["mid_circuit_reset"] = args.mid_circuit_reset
    for item in args.set:
        key, value = item.split("=", 1)
        config["backend"].setdefault("options", {})[key] = _parse_value(value)

    report = schedule_report(
        config,
        args.rounds,
        args.basis,
        active_reset_cycles=args.active_reset_cycles,
        dynamical_decoupling=args.dd,
    )
    print(f"Chip {report['chip']}, end delay between shots {report['end_delay_us']:.1f} us")
    previous = None
    for row in report["rows"]:
        increment = "" if previous is None else f" (+{row['schedule_us'] - previous:.2f} us vs previous)"
        print(
            f"r={row['rounds']}: schedule {row['schedule_us']:.2f} us{increment}; "
            f"per shot {row['per_shot_ms']:.3f} ms; "
            f"{args.shots} shots ~ {row['per_shot_ms'] * args.shots / 1000:.2f} QPU s; ops {row['ops']}"
        )
        previous = row["schedule_us"]
    return 0


def schedule_report(
    config: dict[str, Any],
    rounds: list[int],
    basis: str,
    active_reset_cycles: int | None = None,
    dynamical_decoupling: bool = False,
) -> dict[str, Any]:
    _load_dotenv()
    from iqm.pulla.pulla import Pulla
    from iqm.pulla.utils_qiskit import qiskit_to_pulla
    from iqm.qiskit_iqm import IQMProvider

    server_url = os.environ.get("IQM_SERVER_URL", "https://resonance.meetiqm.com")
    computer = config["backend"].get("options", {}).get("quantum_computer") or os.environ.get("IQM_QUANTUM_COMPUTER")
    pulla = Pulla(server_url, quantum_computer=computer)
    backend = IQMProvider(server_url, quantum_computer=computer).get_backend()

    transpiled = []
    for value in rounds:
        run_config = copy.deepcopy(config)
        run_config["code"]["rounds"] = int(value)
        circuit = get_code_builder(run_config["code"].get("family", "surface_code"))(
            run_config["code"], run_config["noise"], basis
        )
        circuit = prepare_circuit_for_execution(run_config, circuit)
        request = _prepare_iqm_request(run_config["backend"], circuit, run_config["mapping"], backend)
        transpiled.append(request["transpiled_circuit"])

    circuits, compiler = qiskit_to_pulla(pulla, backend, transpiled)
    settings = compiler.get_settings(circuits=circuits)
    if active_reset_cycles is not None:
        settings.stages.timebox_stage.prepend_reset.active_reset_cycles = active_reset_cycles
    if dynamical_decoupling:
        settings.stages.dynamical_decoupling.apply_dd_strategy.dd_is_disabled = False
    context = compiler.compiler_context(None, settings)
    context["timebox_input"] = False
    schedules, context = compiler.run_stages(circuits, context, stages=compiler.circuit_stages + compiler.pulse_stages)

    channel = next(iter(context["builder"].channels.values()))
    end_delay = float(settings.controllers.options.end_delay.value)
    rows = []
    metrics_list = context.get("circuit_metrics", [None] * len(rounds))
    for value, schedule, metrics in zip(rounds, schedules, metrics_list, strict=True):
        seconds = channel.duration_to_seconds(schedule.duration)
        ops = {}
        if metrics is not None:
            ops = {
                name: {impl: sum(counter.values()) for impl, counter in impls.items()}
                for name, impls in metrics.gate_loci.items()
            }
        rows.append(
            {
                "rounds": int(value),
                "schedule_us": seconds * 1e6,
                "per_shot_ms": (seconds + end_delay) * 1e3,
                "ops": ops,
            }
        )
    return {"chip": pulla.get_chip_label(), "end_delay_us": end_delay * 1e6, "rows": rows}


def _parse_value(text: str) -> Any:
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


if __name__ == "__main__":
    raise SystemExit(main())
