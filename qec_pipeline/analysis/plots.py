"""Plots of a metric against the number of rounds, one line per series."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def plot_vs_rounds(
    rows: list[dict[str, Any]],
    output_path: Path,
    y_key: str,
    ylabel: str,
    title: str,
    series: Sequence[str] = ("basis",),
    yerr_key: str | None = None,
    y_max: float | None = 1.0,
    chance_line: bool = False,
    figsize: tuple[float, float] = (7, 4.5),
) -> None:
    """Plot `y_key` against `rounds`, one line per distinct value of the `series` columns.

    Rows without a value for `y_key` are skipped; nothing is written if none remain.
    """
    rows = [row for row in rows if row.get(y_key) not in {None, ""}]
    if not rows:
        return

    fig, ax = plt.subplots(figsize=figsize)
    for key in sorted({tuple(row[name] for name in series) for row in rows}):
        line = sorted((row for row in rows if tuple(row[name] for name in series) == key), key=lambda r: r["rounds"])
        yerr = [float(row.get(yerr_key) or 0.0) for row in line] if yerr_key else None
        ax.errorbar(
            [row["rounds"] for row in line],
            [float(row[y_key]) for row in line],
            yerr=yerr,
            marker="o",
            capsize=3 if yerr else 0,
            label=" ".join(str(part) for part in key),
        )
    if chance_line:
        ax.axhline(0.5, color="0.4", linestyle="--", linewidth=1, label="random LER")
    ax.set_xlabel("Rounds")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(bottom=0.0, top=y_max)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize="small")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
