"""Build the results page's data (site/data/*.json) from the archived baselines.

Every number on the page comes from these files, and these files come only from
tracked archives under baselines/, so the page can be regenerated and checked:

    python scripts/build_site_data.py            # writes site/data/
    python scripts/build_site_data.py --check    # fails if site/data/ is out of date
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qec_pipeline.analysis.metrics import wilson_interval

BASELINES = REPO_ROOT / "baselines"
POST = BASELINES / "post_hackathon"
SITE_DATA = REPO_ROOT / "site" / "data"

LER_RUNS = [
    (
        "jun07_june",
        "June circuit, hackathon (Jun 7)",
        "2026-06-07",
        BASELINES / "hackathon_2026-06-07/surface_d3_iqm_hardware",
    ),
    ("oct12_june", "June circuit, Oct 12", "2026-10-12", POST / "hw_20261012/C_june_design"),
    ("oct04_current", "Current circuit, Oct 4", "2026-10-04", POST / "hw_d3_noreset_dd_20261004"),
    ("oct12_current", "Current circuit, Oct 12", "2026-10-12", POST / "hw_20261012/A_current_design"),
    ("oct12_nodd", "Current circuit without DD, Oct 12", "2026-10-12", POST / "hw_20261012/B_dd_off"),
]
FIT_RUNS = [
    ("oct12_current_corr", "Oct 12, correlated matching", "hardware", POST / "hw_20261012/A_redecoded_correlated"),
    ("oct12_current", "Oct 12", "hardware", POST / "hw_20261012/A_current_design"),
    ("oct12_current_pred", "Oct 12, prediction", "prediction", POST / "hw_20261012_prediction/A_current_design"),
    ("oct12_nodd", "Oct 12, without DD", "hardware", POST / "hw_20261012/B_dd_off"),
    ("oct12_nodd_pred", "Oct 12, without DD, prediction", "prediction", POST / "hw_20261012_prediction/B_dd_off"),
    ("oct04_current", "Oct 4", "hardware", POST / "hw_d3_noreset_dd_20261004"),
    ("oct04_current_pred", "Oct 4, prediction", "prediction", POST / "hw_d3_noreset_dd_prediction_20261004"),
]
RAW_RUNS = [
    ("oct12_june", "June circuit, Oct 12", POST / "hw_20261012/C_diagnosis"),
    ("oct12_current", "Current circuit, Oct 12", POST / "hw_20261012/A_diagnosis"),
]


def build() -> dict[str, list[dict]]:
    ler = []
    for run, label, date, folder in LER_RUNS:
        for row in _csv(folder / "sweep_results.csv"):
            failures, shots = int(row["logical_failures"]), int(row["shots"])
            low, high = wilson_interval(failures, shots)
            ler.append(
                {
                    "run": run,
                    "label": label,
                    "date": date,
                    "basis": row["basis"],
                    "rounds": int(row["rounds"]),
                    "ler": round(failures / shots, 5),
                    "ci_low": round(low, 5),
                    "ci_high": round(high, 5),
                    "failures": failures,
                    "shots": shots,
                    "source": _rel(folder / "sweep_results.csv"),
                }
            )

    fits = []
    for order, (run, label, kind, folder) in enumerate(FIT_RUNS):
        per_basis = json.loads((folder / "sweep_results.json").read_text(encoding="utf-8"))["per_round_fits"]
        for basis in sorted(per_basis):
            fit = per_basis[basis]
            fits.append(
                {
                    "key": f"{run}|{basis}",
                    "run": run,
                    "label": label,
                    "kind": kind,
                    "basis": basis,
                    "order": order,
                    "eps": round(fit["fitted_logical_error_per_round"], 5),
                    "sigma": round(fit["fitted_logical_error_per_round_uncertainty"], 5),
                    "rounds_fitted": fit["fit_points"],
                    "source": _rel(folder / "sweep_results.json"),
                }
            )

    raw = []
    for run, label, folder in RAW_RUNS:
        for row in _csv(folder / "round_diagnostics.csv"):
            raw.append(
                {
                    "run": run,
                    "label": label,
                    "basis": row["basis"],
                    "rounds": int(row["rounds"]),
                    "raw_flip": round(float(row["raw_observable_flip_rate"]), 4),
                    "shots": int(row["shots"]),
                    "source": _rel(folder / "round_diagnostics.csv"),
                }
            )

    round_time = [
        {
            "variant": row["variant"],
            "short": row["short"],
            "us": float(row["us_per_round"]),
            "order": int(row["order"]),
            "source": _rel(POST / "round_time_pulla_20261012.csv"),
        }
        for row in _csv(POST / "round_time_pulla_20261012.csv")
    ]
    jobs = [
        {
            "date": row["date"],
            "job": row["job"],
            "what": row["what"],
            "shots": int(row["shots"]),
            "qpu_s": float(row["qpu_execution_s"]),
            "outcome": row["outcome"],
            "archive": row["archive"],
        }
        for row in _csv(POST / "hardware_jobs.csv")
    ]

    key = lambda r: (r["run"], r["basis"], r["rounds"])  # noqa: E731
    return {
        "ler_by_round": sorted(ler, key=key),
        "error_per_round": fits,
        "raw_observable": sorted(raw, key=key),
        "round_time": round_time,
        "hardware_jobs": jobs,
    }


def render(data: dict[str, list[dict]]) -> dict[str, str]:
    return {f"{name}.json": json.dumps(rows, indent=1, ensure_ascii=False) + "\n" for name, rows in data.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Exit 1 if site/data differs from the archives.")
    args = parser.parse_args()

    files = render(build())
    if args.check:
        stale = [name for name, text in files.items() if _read(SITE_DATA / name) != text]
        if stale:
            print(f"site/data is out of date: {stale}. Run python scripts/build_site_data.py")
            return 1
        print("site/data matches the archives")
        return 0
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (SITE_DATA / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {len(files)} files to {SITE_DATA.relative_to(REPO_ROOT)}")
    return 0


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


if __name__ == "__main__":
    raise SystemExit(main())
