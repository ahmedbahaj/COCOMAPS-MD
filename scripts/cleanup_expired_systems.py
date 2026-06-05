#!/usr/bin/env python3
"""
Remove stale data under systems/.

Completed analyses are removed when their _metadata.json jobExpiresAt is in the
past. Failed job records are removed after a shorter retention window, along
with their partial system folders only when those folders do not contain valid
analysis metadata.

Run from repo root, or anywhere if PYTHONPATH includes the repo root — the script
prepends its parent directory so `engine` resolves when executed as a file.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Allow `python scripts/cleanup_expired_systems.py` without PYTHONPATH=. (Docker: /app)
_root = _repo_root()
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from engine.job_id import _parse_iso_utc  # noqa: E402

FAILED_JOB_RETENTION_DAYS = 7


def _load_metadata(system_dir: Path) -> dict | None:
    path = system_dir / "_metadata.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _jobs_file(systems_dir: Path) -> Path:
    return systems_dir / ".jobs.json"


def _load_jobs(systems_dir: Path) -> dict:
    path = _jobs_file(systems_dir)
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_jobs(systems_dir: Path, jobs: dict) -> None:
    path = _jobs_file(systems_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
        f.write("\n")


def _partial_system_path(systems_dir: Path, system_id: object) -> Path | None:
    """Return a safe child path for a failed job's partial system directory."""
    if not isinstance(system_id, str) or not system_id.strip():
        return None
    if "/" in system_id or "\\" in system_id or system_id.startswith("."):
        return None
    candidate = (systems_dir / system_id).resolve()
    systems_root = systems_dir.resolve()
    if candidate.parent != systems_root:
        return None
    return candidate


def iter_expired(
    systems_dir: Path, *, now: datetime | None = None
) -> list[tuple[Path, str]]:
    """Return [(path, reason)] for dirs that should be deleted (expired, not example)."""
    if now is None:
        now = datetime.now(timezone.utc)
    if not systems_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {systems_dir}")

    expired: list[tuple[Path, str]] = []
    for child in sorted(systems_dir.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        meta = _load_metadata(child)
        if meta is None:
            continue
        if meta.get("isExample") is True:
            continue
        raw = meta.get("jobExpiresAt")
        expires = _parse_iso_utc(raw) if raw else None
        if expires is None:
            continue
        if expires <= now:
            expired.append((child, expires.isoformat()))
    return expired


def iter_failed_jobs(
    systems_dir: Path,
    *,
    now: datetime | None = None,
    days_valid: int = FAILED_JOB_RETENTION_DAYS,
) -> list[tuple[str, Path | None, str]]:
    """
    Return failed jobs old enough to prune.

    The job record is pruned when status == failed and created_at is older than
    days_valid. A partial folder is returned only when it is a direct child of
    systems_dir and lacks valid _metadata.json; completed-looking folders remain
    governed by jobExpiresAt cleanup.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not systems_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {systems_dir}")

    jobs = _load_jobs(systems_dir)
    failed: list[tuple[str, Path | None, str]] = []
    cutoff = now.timestamp() - (int(days_valid) * 24 * 60 * 60)

    for job_id, job in sorted(jobs.items()):
        if not isinstance(job, dict) or job.get("status") != "failed":
            continue

        created = _parse_iso_utc(job.get("created_at"))
        if created is None or created.timestamp() > cutoff:
            continue

        partial_path = _partial_system_path(systems_dir, job.get("system_id"))
        if partial_path is not None:
            if not partial_path.is_dir() or _load_metadata(partial_path) is not None:
                partial_path = None

        failed.append((str(job_id), partial_path, created.isoformat()))

    return failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete expired systems and stale failed jobs (see scripts/README.md)."
    )
    parser.add_argument(
        "--systems-dir",
        type=Path,
        default=None,
        help="Path to systems/ (default: $COCOMAPS_SYSTEMS_DIR or <repo>/systems).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete folders. Without this, dry-run only.",
    )
    parser.add_argument(
        "--failed-days",
        type=int,
        default=FAILED_JOB_RETENTION_DAYS,
        help=f"Days to retain failed job records/partials (default: {FAILED_JOB_RETENTION_DAYS}).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print deleted paths (or warnings); suppress summary when dry-run empty.",
    )
    args = parser.parse_args()

    if args.systems_dir is not None:
        systems_dir = args.systems_dir.expanduser().resolve()
    else:
        env = __import__("os").environ.get("COCOMAPS_SYSTEMS_DIR", "").strip()
        systems_dir = Path(env).resolve() if env else (_repo_root() / "systems").resolve()

    try:
        candidates = iter_expired(systems_dir)
        failed_jobs = iter_failed_jobs(systems_dir, days_valid=args.failed_days)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    prefix = "" if args.apply else "[dry-run] "

    action = "delete" if args.apply else "would delete"
    failed_action = "prune" if args.apply else "would prune"

    for path, iso in candidates:
        if not args.quiet:
            print(f"{prefix}{action}: {path} (expired {iso})", flush=True)

    for job_id, partial_path, iso in failed_jobs:
        if not args.quiet:
            target = f" and partial folder {partial_path}" if partial_path else ""
            print(f"{prefix}{failed_action} failed job {job_id}{target} (created {iso})", flush=True)

    if not candidates and not failed_jobs:
        if not args.quiet:
            total = sum(1 for p in systems_dir.iterdir() if p.is_dir()) if systems_dir.is_dir() else 0
            print(f"No expired systems or stale failed jobs under {systems_dir} ({total} system dirs scanned).")

    if args.apply:
        errs = 0
        for path, _iso in candidates:
            try:
                shutil.rmtree(path)
                print(f"deleted: {path}", flush=True)
            except OSError as e:
                errs += 1
                print(f"error deleting {path}: {e}", file=sys.stderr)

        if failed_jobs:
            jobs = _load_jobs(systems_dir)
            for job_id, partial_path, _iso in failed_jobs:
                jobs.pop(job_id, None)
                if partial_path is None:
                    continue
                try:
                    shutil.rmtree(partial_path)
                    print(f"deleted partial failed job folder: {partial_path}", flush=True)
                except OSError as e:
                    errs += 1
                    print(f"error deleting {partial_path}: {e}", file=sys.stderr)
            try:
                _write_jobs(systems_dir, jobs)
                print(f"pruned {len(failed_jobs)} failed job record(s)", flush=True)
            except OSError as e:
                errs += 1
                print(f"error writing {_jobs_file(systems_dir)}: {e}", file=sys.stderr)
        return 1 if errs else 0

    if (candidates or failed_jobs) and not args.quiet:
        print("\nDry-run only. Pass --apply to perform these cleanup actions.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
