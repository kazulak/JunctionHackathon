"""Verify the provenance claims in PROVENANCE.md from the git history alone.

Checks:
1. The submission tags point at the expected commits.
2. The submission zip stored in the checkpoint commit has the expected SHA-256.
3. Every file in the zip that also exists in the submission commit is identical
   (line endings normalized).
4. IQM job IDs found under baselines/ are decoded to their UUIDv7 submit times.

Run from the repository root:

    python scripts/verify_submission.py
"""

from __future__ import annotations

import hashlib
import io
import re
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

SUBMISSION_COMMIT = "16e86b15860e089933a6cdf0d58931253abe31f5"
CHECKPOINT_COMMIT = "3cfa7149549b9f4d59aaafb865cb56a6a6f0e01a"
EXPECTED_TAGS = {
    "hackathon-submission-2026-06-07": SUBMISSION_COMMIT,
    "junction-quantum-hackathon-final-2026": CHECKPOINT_COMMIT,
}
ZIP_PATH = "gate_crushers_submission_20260607_085338.zip"
ZIP_SHA256 = "248c62a0072bebed92ce9b04b375af564c6d484191e5e372c9fabc5dd522260c"
UUID7_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}\b")


def main() -> int:
    failures = 0
    failures += _check_tags()
    zip_bytes = _git_bytes("show", f"{CHECKPOINT_COMMIT}:{ZIP_PATH}")
    failures += _check_zip_hash(zip_bytes)
    failures += _check_zip_matches_commit(zip_bytes)
    _print_job_times(Path("baselines"))

    print()
    print("RESULT:", "OK" if failures == 0 else f"{failures} check(s) failed")
    return 0 if failures == 0 else 1


def _check_tags() -> int:
    failures = 0
    print("Tags")
    for tag, expected in EXPECTED_TAGS.items():
        try:
            actual = _git_text("rev-parse", f"{tag}^{{commit}}")
        except subprocess.CalledProcessError:
            print(f"  FAIL {tag}: not found (run `git fetch --tags`)")
            failures += 1
            continue
        status = "ok  " if actual == expected else "FAIL"
        failures += actual != expected
        print(f"  {status} {tag} -> {actual[:7]} (expected {expected[:7]})")
    return failures


def _check_zip_hash(zip_bytes: bytes) -> int:
    digest = hashlib.sha256(zip_bytes).hexdigest()
    ok = digest == ZIP_SHA256
    print("Submission zip")
    print(f"  {'ok  ' if ok else 'FAIL'} sha256 {digest}")
    return 0 if ok else 1


def _check_zip_matches_commit(zip_bytes: bytes) -> int:
    archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    zip_files = {
        info.filename: archive.read(info.filename)
        for info in archive.infolist()
        if not info.is_dir()
    }
    tree = set(_git_text("ls-tree", "-r", "--name-only", SUBMISSION_COMMIT).splitlines())

    identical, differing = [], []
    for name, content in sorted(zip_files.items()):
        if name not in tree:
            continue
        committed = _git_bytes("show", f"{SUBMISSION_COMMIT}:{name}")
        if _normalize(committed) == _normalize(content):
            identical.append(name)
        else:
            differing.append(name)

    only_zip = sorted(set(zip_files) - tree)
    only_git = sorted(tree - set(zip_files))
    print(f"Zip vs commit {SUBMISSION_COMMIT[:7]}")
    print(f"  identical: {len(identical)}  differing: {len(differing)}")
    for name in differing:
        print(f"  FAIL differs: {name}")
    print(f"  only in zip (gitignored data): {len(only_zip)}")
    print(f"  only in git (reference material): {len(only_git)}")
    return 1 if differing else 0


def _print_job_times(root: Path) -> None:
    jobs: dict[str, set[str]] = {}
    for path in root.rglob("*"):
        if path.suffix not in {".csv", ".json", ".md"}:
            continue
        for job_id in UUID7_RE.findall(path.read_text(encoding="utf-8-sig", errors="ignore")):
            jobs.setdefault(job_id, set()).add(path.parent.relative_to(root).as_posix())
    print("IQM jobs in baselines/ (UUIDv7 submit time, UTC)")
    for job_id in sorted(jobs):
        print(f"  {uuid7_time(job_id).isoformat(timespec='seconds')} {job_id} {sorted(jobs[job_id])}")


def uuid7_time(job_id: str) -> datetime:
    """Return the millisecond timestamp embedded in a UUIDv7."""
    milliseconds = int(job_id.replace("-", "")[:12], 16)
    return datetime.fromtimestamp(milliseconds / 1000, UTC)


def _normalize(content: bytes) -> bytes:
    return content.replace(b"\r\n", b"\n")


def _git_bytes(*args: str) -> bytes:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def _git_text(*args: str) -> str:
    return _git_bytes(*args).decode("utf-8").strip()


if __name__ == "__main__":
    sys.exit(main())
