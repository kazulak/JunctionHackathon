from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print worst ideal-vs-observed measurement diagnostics from a run."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Result directory, basis directory, or direct measurement_diagnostics.json path.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=8,
        help="Number of rows to print per basis.",
    )
    args = parser.parse_args()

    paths = find_diagnostic_files(args.path)
    if not paths:
        raise SystemExit(f"No measurement_diagnostics.json files found under {args.path}")

    for path in paths:
        print(f"\n{path.parent.name}")
        rows = json.loads(path.read_text(encoding="utf-8"))
        deterministic = [row for row in rows if row.get("deterministic_value") is not None]
        worst = sorted(
            deterministic,
            key=lambda row: float(row.get("unexpected_rate", 0.0)),
            reverse=True,
        )[: args.top]
        for row in worst:
            print(
                "m={measurement_index:>2} stim={stim_qubit!s:>2} "
                "hw={hardware_qubit!s:>5} ideal={ideal_one_rate:.3f} "
                "observed={observed_one_rate:.3f} unexpected={unexpected_rate:.3f}".format(
                    **row
                )
            )

    return 0


def find_diagnostic_files(path: Path) -> list[Path]:
    if path.is_file() and path.name == "measurement_diagnostics.json":
        return [path]
    if path.is_dir() and (path / "measurement_diagnostics.json").exists():
        return [path / "measurement_diagnostics.json"]
    if path.is_dir():
        files = sorted(path.glob("*/measurement_diagnostics.json"))
        if files:
            return files
        child_dirs = sorted([child for child in path.iterdir() if child.is_dir()])
        if child_dirs:
            return sorted(child_dirs[-1].glob("*/measurement_diagnostics.json"))
    return []


if __name__ == "__main__":
    raise SystemExit(main())
