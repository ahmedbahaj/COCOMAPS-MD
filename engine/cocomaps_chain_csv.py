"""
Rewrite Chain 1 / Chain 2 in CoCoMaps distance-table CSVs after a run.

The vendored CoCoMaps package uses internal placeholders in early outputs
(full.csv, trial24.csv). Final interaction CSVs are remapped inside CoCoMaps,
but those distance dumps keep @ / ! unless we normalize them here using the
same chain IDs passed in example_input.json (chains_set_1 / chains_set_2).
"""

from __future__ import annotations

import csv
from pathlib import Path

# Mirrors cocomaps.constants CHAIN1_IDENTIFIER / CHAIN2_IDENTIFIER (do not import cocomaps here).
_PLACEHOLDER_FIRST = "@"
_PLACEHOLDER_SECOND = "!"

_COL_CHAIN_1 = "Chain 1"
_COL_CHAIN_2 = "Chain 2"


def _map_cell(value: str, chain_a: str, chain_b: str) -> str:
    v = (value or "").strip()
    if v == _PLACEHOLDER_FIRST:
        return chain_a
    if v == _PLACEHOLDER_SECOND:
        return chain_b
    return value


def remap_distance_table_csv(path: Path, chain_a: str, chain_b: str) -> bool:
    """
    In-place: replace @ and ! in Chain 1 / Chain 2 with PDB chain IDs.
    Returns True if the file was read and written, False if skipped.
    """
    if not path.is_file():
        return False
    ca = str(chain_a).strip()
    cb = str(chain_b).strip()
    if not ca or not cb:
        return False

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or _COL_CHAIN_1 not in fieldnames or _COL_CHAIN_2 not in fieldnames:
            return False
        rows = list(reader)

    changed = False
    for row in rows:
        o1, o2 = row.get(_COL_CHAIN_1), row.get(_COL_CHAIN_2)
        n1 = _map_cell(o1 or "", ca, cb)
        n2 = _map_cell(o2 or "", ca, cb)
        if n1 != o1 or n2 != o2:
            changed = True
        row[_COL_CHAIN_1] = n1
        row[_COL_CHAIN_2] = n2

    if not changed:
        return True

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return True


def remap_frame_distance_outputs(frame_dir: Path, chain_a: str, chain_b: str) -> None:
    """Normalize chain columns in standard CoCoMaps distance-table files under frame_dir."""
    for name in ("full.csv", "trial24.csv"):
        remap_distance_table_csv(frame_dir / name, chain_a, chain_b)
