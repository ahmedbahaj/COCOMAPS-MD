#!/usr/bin/env python3
"""
Remove analysed system folders under systems/ whose jobExpiresAt is in the past.

Skips bundles marked isExample and dirs without a valid jobExpiresAt (safe-by-default).

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete systems/<id>/ folders past jobExpiresAt (see scripts/README.md)."
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
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    prefix = "" if args.apply else "[dry-run] "

    for path, iso in candidates:
        if not args.quiet:
            print(f"{prefix}would delete: {path} (expired {iso})", flush=True)

    if not candidates:
        if not args.quiet:
            total = sum(1 for p in systems_dir.iterdir() if p.is_dir()) if systems_dir.is_dir() else 0
            print(f"No expired job folders under {systems_dir} ({total} system dirs scanned).")

    if args.apply:
        errs = 0
        for path, _iso in candidates:
            try:
                shutil.rmtree(path)
                print(f"deleted: {path}", flush=True)
            except OSError as e:
                errs += 1
                print(f"error deleting {path}: {e}", file=sys.stderr)
        return 1 if errs else 0

    if candidates and not args.quiet:
        print("\nDry-run only. Pass --apply to remove these folders.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
