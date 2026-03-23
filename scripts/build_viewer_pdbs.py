"""
Build frame_1/frame_1_viewer.pdb for existing systems that still have their original PDB.

Only systems with `<systems_dir>/<name>/<name>.pdb` are processed (same name as the folder).
Systems without that file (e.g. deleted to save space) are skipped.

Requires: _interactions.csv and a finished pipeline under each system (including
``frame_1/frame_1.pdb`` and CoCoMaps CSVs such as ``*_Water_Mediated.csv`` — the
engine uses those for bridging waters). MDAnalysis required.

Usage (from project root):
  python scripts/build_viewer_pdbs.py
  python scripts/build_viewer_pdbs.py --dry-run
  python scripts/build_viewer_pdbs.py --systems-dir path/to/systems --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.viewer_pdb import write_viewer_frame_pdb


def original_pdb_path(system_dir: Path) -> Path:
    return system_dir / f"{system_dir.name}.pdb"


def iter_system_dirs(systems_dir: Path):
    if not systems_dir.is_dir():
        raise SystemExit(f"Systems directory not found: {systems_dir}")
    for p in sorted(systems_dir.iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            yield p


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate frame_1_viewer.pdb for systems that have <name>/<name>.pdb"
    )
    parser.add_argument(
        "--systems-dir",
        type=Path,
        default=PROJECT_ROOT / "systems",
        help="Directory containing system folders (default: <project>/systems)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List systems that would be processed; do not write files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if frame_1/frame_1_viewer.pdb already exists",
    )
    args = parser.parse_args()

    systems_dir = args.systems_dir.resolve()
    dry = args.dry_run
    force = args.force

    ok = 0
    skipped_no_pdb = 0
    skipped_no_interactions = 0
    skipped_exists = 0
    failed = 0

    for system_dir in iter_system_dirs(systems_dir):
        name = system_dir.name
        orig = original_pdb_path(system_dir)
        interactions = system_dir / "_interactions.csv"
        viewer_out = system_dir / "frame_1" / "frame_1_viewer.pdb"

        if not orig.is_file():
            skipped_no_pdb += 1
            continue

        if not interactions.is_file():
            print(f"[skip] {name}: no _interactions.csv")
            skipped_no_interactions += 1
            continue

        if viewer_out.is_file() and not force:
            if dry:
                print(f"[dry-run] skip (viewer exists): {name}")
            else:
                print(f"[skip] {name}: frame_1_viewer.pdb exists (use --force to overwrite)")
            skipped_exists += 1
            continue

        if dry:
            print(f"[dry-run] would build: {name}  ({orig.name})")
            ok += 1
            continue

        print(f"[build] {name} ...", flush=True)
        try:
            written = write_viewer_frame_pdb(
                system_dir,
                start_frame=0,
                end_frame=-1,
                frame_step=1,
                verbose=True,
            )
            if written:
                ok += 1
            else:
                print(f"[warn] {name}: write_viewer_frame_pdb returned False")
                failed += 1
        except Exception as e:
            print(f"[error] {name}: {e}")
            failed += 1

    print()
    print(
        f"Done. built={ok}  skipped_no_matching_pdb={skipped_no_pdb}  "
        f"skipped_no_interactions={skipped_no_interactions}  skipped_exists={skipped_exists}  failed={failed}"
    )


if __name__ == "__main__":
    main()
