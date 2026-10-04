"""Provenance helpers: which code produced a result, and when."""

from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKED_PACKAGES = ("stim", "PyMatching", "numpy", "qiskit", "iqm-client")


def uuid7_time(job_id: str) -> datetime:
    """Return the UTC submit time embedded in a UUIDv7 (e.g. an IQM job ID)."""
    milliseconds = int(str(job_id).replace("-", "")[:12], 16)
    return datetime.fromtimestamp(milliseconds / 1000, UTC)


def run_provenance() -> dict[str, Any]:
    """Describe the code and environment of the current run.

    Fails soft: missing git or packages are recorded as None instead of raising.
    """
    return {
        "recorded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": _git_dirty(),
        "python": platform.python_version(),
        "packages": {name: _package_version(name) for name in TRACKED_PACKAGES},
    }


def provenance_line(provenance: dict[str, Any]) -> str:
    """One-line Markdown summary for summary files."""
    commit = (provenance.get("git_commit") or "unknown")[:7]
    dirty = " (uncommitted changes)" if provenance.get("git_dirty") else ""
    return f"- Code: `{commit}`{dirty} on `{provenance.get('git_branch')}`, recorded {provenance.get('recorded_utc')}"


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _git_dirty() -> bool | None:
    status = _git("status", "--porcelain", "--untracked-files=no")
    if status is None:
        return None if _git("rev-parse", "HEAD") is None else False
    return True


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None
