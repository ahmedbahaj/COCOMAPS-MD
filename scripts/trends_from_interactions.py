#!/usr/bin/env python3
"""
Build _trends.csv from _interactions.csv by counting normalized interaction types per frame.

Each residue-pair row contributes +1 to every interaction type listed in its `types` field
(after splitting on ';' and normalizing). Column names match backend/routes/data.py TRENDS_KEYS.

Usage:
  python scripts/trends_from_interactions.py systems/my_system
  python scripts/trends_from_interactions.py path/to/_interactions.csv -o path/to/_trends.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

# Must match backend/routes/data.py TRENDS_KEYS (order preserved for CSV columns).
TRENDS_KEYS = [
    "H-bonds",
    "Salt-bridges",
    "π-π interactions",
    "Cation-π interactions",
    "Anion-π interactions",
    "CH-O/N bonds",
    "CH-π interactions",
    "Halogen bonds",
    "Apolar vdW contacts",
    "Polar vdW contacts",
    "Proximal contacts",
    "Clashes",
    "Water mediated",
    "Metal mediated",
    "S-S bonds",
    "Amino-π interactions",
    "Lone pair-π interactions",
    "O/N/SH-π interactions",
]


def _import_normalize():
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from engine.aggregate_csv import _normalize_interaction_type

    return _normalize_interaction_type


def normalized_to_trend_key(normalized: str) -> str | None:
    """Map output of _normalize_interaction_type to a TRENDS_KEYS column name."""
    if not normalized:
        return None
    n = normalized.strip()
    # Labels that differ between normalization and trends CSV / API.
    special = {
        "H-bond": "H-bonds",
        "Salt-bridge": "Salt-bridges",
        "Water-mediated contacts": "Water mediated",
        "Metal-mediated contacts": "Metal mediated",
        "lp-π interactions": "Lone pair-π interactions",
        "S-S bond": "S-S bonds",
    }
    if n in special:
        return special[n]
    if n in TRENDS_KEYS:
        return n
    return None


def build_trends_counts(interactions_path: Path) -> tuple[list[int], dict[str, list[int]]]:
    _normalize_interaction_type = _import_normalize()
    # frame -> trend_key -> count
    per_frame: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    with open(interactions_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "frame" not in (reader.fieldnames or []) or "types" not in (reader.fieldnames or []):
            raise SystemExit(
                f"Expected columns 'frame' and 'types' in {interactions_path}, got {reader.fieldnames}"
            )
        for row in reader:
            try:
                frame = int(row["frame"])
            except (TypeError, ValueError):
                continue
            raw = row.get("types") or ""
            for part in raw.split(";"):
                nt = _normalize_interaction_type(part.strip())
                if not nt:
                    continue
                key = normalized_to_trend_key(nt)
                if key is None:
                    continue
                per_frame[frame][key] += 1

    frames = sorted(per_frame.keys())
    trends: dict[str, list[int]] = {k: [] for k in TRENDS_KEYS}
    for fr in frames:
        counts = per_frame[fr]
        for k in TRENDS_KEYS:
            trends[k].append(counts.get(k, 0))
    return frames, trends


def write_trends_csv(out_path: Path, frames: list[int], trends: dict[str, list[int]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["frame"] + TRENDS_KEYS
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i, fr in enumerate(frames):
            row = {"frame": fr}
            for k in TRENDS_KEYS:
                row[k] = trends[k][i]
            w.writerow(row)


def main() -> None:
    p = argparse.ArgumentParser(description="Write _trends.csv from _interactions.csv")
    p.add_argument(
        "path",
        help="System directory (containing _interactions.csv) or path to _interactions.csv",
    )
    p.add_argument(
        "-o",
        "--output",
        help="Output _trends.csv path (default: <system>/_trends.csv next to interactions file)",
    )
    args = p.parse_args()
    raw = Path(args.path)
    if raw.is_dir():
        interactions = raw / "_interactions.csv"
        default_out = raw / "_trends.csv"
    else:
        interactions = raw
        default_out = interactions.parent / "_trends.csv"

    if not interactions.is_file():
        raise SystemExit(f"Not found: {interactions}")

    out = Path(args.output) if args.output else default_out
    frames, trends = build_trends_counts(interactions)
    if not frames:
        raise SystemExit("No rows with valid frame numbers in interactions file.")

    write_trends_csv(out, frames, trends)
    print(f"Wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
