"""
Mol* viewer PDB: first processed frame only.

Contains **all chains** (protein / DNA / ligand) from the original uploaded PDB's
first processed frame, plus **mediated waters / metals / ions** that appear in
frame 1's mediated-interaction data.  Both use first-frame coordinates.

Mediated identities come from:
  - System-level ``_water_mediated.csv`` / ``_metal_mediated.csv`` filtered to
    frame 1, **or** per-frame ``frame_1/*_Water_Mediated.csv`` /
    ``frame_1/*_Metal_Mediated.csv`` as a fallback.
  - Atom coordinates are extracted directly from the frame 1 trimmed PDB.

Web upload only (not used by CLI).
"""
from __future__ import annotations

import csv
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Set, Tuple

import numpy as np
import MDAnalysis as mda

from engine.interface_selector import METALS

# Waters before/after rename; CoCoMaps output uses HOH, original may use SOL/WAT/TIP3
WATER_RESNAMES = frozenset(
    {"HOH", "H2O", "WAT", "TIP3", "TIP4", "SOL", "DOD"}
)

# Uppercase metal resnames for lookup
_METAL_UPPER = {m.upper() for m in METALS}

# Halide / simple ions not listed in METALS (METALS already covers Na, K, Mg, etc.).
# Chloride (resname CL) was slipping through as "everything else" and cluttering the viewer.
ION_RESNAMES = frozenset({"CL", "IOD"})
_ION_UPPER = {x.upper() for x in ION_RESNAMES}


def _parse_raw_frames(pdb_path: Path) -> list:
    """Split PDB text into frame blocks (same rules as analyze_pdb.process_frames)."""
    raw_frames = []
    with open(pdb_path, "r", encoding="utf-8", errors="replace") as fh:
        current_frame_lines = []
        in_model = False
        for line in fh:
            record = line[:6].strip()
            if record == "MODEL":
                in_model = True
                current_frame_lines = [line]
            elif record == "ENDMDL":
                current_frame_lines.append(line)
                raw_frames.append("".join(current_frame_lines))
                current_frame_lines = []
                in_model = False
            elif in_model:
                current_frame_lines.append(line)

    if not raw_frames:
        with open(pdb_path, "r", encoding="utf-8", errors="replace") as fh:
            current_frame_lines = []
            for line in fh:
                record = line[:6].strip()
                if record == "END":
                    if current_frame_lines:
                        raw_frames.append("".join(current_frame_lines))
                        current_frame_lines = []
                else:
                    current_frame_lines.append(line)
            if current_frame_lines:
                raw_frames.append("".join(current_frame_lines))

    return raw_frames


def _find_original_pdb(system_path: Path) -> Optional[Path]:
    """Top-level .pdb copy (uploaded file saved by process_frames)."""
    candidates = sorted(system_path.glob("*.pdb"))
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    stem = system_path.name
    for p in candidates:
        if p.stem == stem:
            return p
    return candidates[0]


def _normalize_resnum(val) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _residue_key(atom) -> Tuple[str, int]:
    ch = atom.chainID
    if not (ch and str(ch).strip()):
        ch = getattr(atom, "segid", None) or ""
    ch = str(ch).strip()
    try:
        rn = int(atom.resid)
    except (TypeError, ValueError):
        rn = int(float(str(atom.resid)))
    return (ch, rn)


def _get_chain_pattern(frame_folder: Path) -> str:
    """Detect chain pattern (e.g. 'A_B') from CSV filenames in a frame folder."""
    pattern = re.compile(r"\.pd[b_h\.]*_([A-Z])_([A-Z])_final_file\.csv$")
    for f in frame_folder.iterdir():
        if f.is_file():
            match = pattern.search(f.name)
            if match:
                return f"{match.group(1)}_{match.group(2)}"
    return "A_B"


def _find_final_files(system_dir: Path) -> list[Path]:
    """
    Discover all *_final_file.csv paths (same logic as conserved_islands, without importing it).
    """
    frame_folders = sorted(
        [f for f in system_dir.iterdir() if f.is_dir() and f.name.startswith("frame_")],
        key=lambda f: int(f.name.split("_")[1]) if "_" in f.name else 0,
    )
    csv_paths = []
    for frame_folder in frame_folders:
        chain_pattern = _get_chain_pattern(frame_folder)
        csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_{chain_pattern}_final_file.csv"
        if not csv_file.exists():
            csv_file = frame_folder / f"{frame_folder.name}.pdb_{chain_pattern}_final_file.csv"
        if csv_file.exists():
            csv_paths.append(csv_file)
    return csv_paths


def _norm_chain(chain) -> str:
    if chain is None:
        return ""
    return str(chain).strip()


def _add_residue_key(
    rname_raw: str,
    rnum_raw,
    chain_raw,
    water_keys: Set[Tuple[str, int]],
    metal_keys: Set[Tuple[str, int]],
    ion_keys: Set[Tuple[str, int]],
) -> None:
    rname = str(rname_raw).strip().upper()
    ch = _norm_chain(chain_raw)
    rn = _normalize_resnum(rnum_raw)
    if rn is None or not rname:
        return
    key = (ch, rn)
    if rname in WATER_RESNAMES:
        water_keys.add(key)
    elif rname in _METAL_UPPER:
        metal_keys.add(key)
    elif rname in _ION_UPPER:
        ion_keys.add(key)


def _collect_keys_from_interactions_csv(
    interactions_csv: Path,
) -> Tuple[Set[Tuple[str, int]], Set[Tuple[str, int]], Set[Tuple[str, int]]]:
    """Keys from aggregated _interactions.csv (often missing explicit waters for water-mediated rows)."""
    water_keys: Set[Tuple[str, int]] = set()
    metal_keys: Set[Tuple[str, int]] = set()
    ion_keys: Set[Tuple[str, int]] = set()

    with open(interactions_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for prefix in ("1", "2"):
                name = row.get(f"resName{prefix}")
                num = row.get(f"resNum{prefix}")
                chain = row.get(f"chain{prefix}")
                if not name or chain is None:
                    continue
                _add_residue_key(name, num, chain, water_keys, metal_keys, ion_keys)

    return water_keys, metal_keys, ion_keys


def _collect_keys_from_final_files(
    system_path: Path,
) -> Tuple[Set[Tuple[str, int]], Set[Tuple[str, int]], Set[Tuple[str, int]]]:
    """Keys from CoCoMaps final_file CSVs (lists actual HOH/SOL/metal/ion partners)."""
    water_keys: Set[Tuple[str, int]] = set()
    metal_keys: Set[Tuple[str, int]] = set()
    ion_keys: Set[Tuple[str, int]] = set()

    for csv_path in _find_final_files(system_path):
        try:
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not all(
                        k in row
                        for k in (
                            "Res. Name 1",
                            "Res. Number 1",
                            "Res. Name 2",
                            "Res. Number 2",
                        )
                    ):
                        continue
                    c1 = row.get("Chain 1") or row.get("Res. Chain 1")
                    c2 = row.get("Chain 2") or row.get("Res. Chain 2")
                    if c1 is None or c2 is None:
                        continue
                    _add_residue_key(
                        row["Res. Name 1"],
                        row["Res. Number 1"],
                        c1,
                        water_keys,
                        metal_keys,
                        ion_keys,
                    )
                    _add_residue_key(
                        row["Res. Name 2"],
                        row["Res. Number 2"],
                        c2,
                        water_keys,
                        metal_keys,
                        ion_keys,
                    )
        except OSError:
            continue

    return water_keys, metal_keys, ion_keys


def _find_trimmed_frame_pdb(frame_folder: Path) -> Optional[Path]:
    """Interface PDB used as CoCoMaps input (prefer no-reduce name)."""
    for name in (f"{frame_folder.name}.pdb", f"{frame_folder.name}.pd_h.pdb"):
        p = frame_folder / name
        if p.is_file():
            return p
    return None


def _parse_cocomaps_identity_token(raw: str) -> Optional[Tuple[str, int, str]]:
    """
    Parse CoCoMaps Water/Metal Identity tokens, e.g. 'X_4300_HOH', 'A_12_MG'.
    Returns (chain, resnum, resname) with chain normalized.
    """
    s = str(raw).strip()
    if not s:
        return None
    parts = s.split("_")
    if len(parts) < 3:
        return None
    resname = parts[-1].strip().upper()
    try:
        resnum = int(parts[-2])
    except ValueError:
        return None
    chain = parts[0] if len(parts) == 3 else "_".join(parts[:-2])
    return (_norm_chain(chain), resnum, resname)


def _get_row_value(row: dict, logical_name: str) -> Optional[str]:
    for k in row:
        if k and k.strip() == logical_name:
            v = row.get(k)
            return str(v).strip() if v is not None else None
    return None


def _sorted_frame_dirs(system_path: Path) -> list[Path]:
    """frame_1, frame_2, … under a system directory."""
    dirs = [
        f
        for f in system_path.iterdir()
        if f.is_dir() and f.name.startswith("frame_") and "_" in f.name
    ]
    return sorted(dirs, key=lambda p: int(p.name.split("_")[1]))


def _parse_frame_cell(row: dict) -> Optional[int]:
    raw = row.get("frame")
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except (ValueError, TypeError):
        return None


def _add_identities_from_mediated_aggregate_rows(
    rows: list[dict],
    col_logical: str,
    dest: Set[Tuple[str, int, str]],
    *,
    frame_filter: Optional[int],
) -> None:
    for row in rows:
        if frame_filter is not None:
            fr = _parse_frame_cell(row)
            if fr is None or fr != frame_filter:
                continue
        tok = _get_row_value(row, col_logical)
        if not tok:
            continue
        p = _parse_cocomaps_identity_token(tok)
        if p:
            dest.add(p)


def _read_aggregate_mediated_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                out: dict = {}
                for k in reader.fieldnames or []:
                    if k is None:
                        continue
                    out[k.strip()] = row.get(k, "")
                rows.append(out)
    except OSError:
        pass
    return rows


def _collect_mediated_identities_from_frame_folders(
    system_path: Path,
    *,
    first_frame_only: bool = False,
) -> Tuple[Set[Tuple[str, int, str]], Set[Tuple[str, int, str]]]:
    """Parse Water/Metal Identity from frame_N/*_Water_Mediated.csv (fallback when no aggregates)."""
    water_id: Set[Tuple[str, int, str]] = set()
    metal_id: Set[Tuple[str, int, str]] = set()
    frame_dirs = _sorted_frame_dirs(system_path)
    if first_frame_only:
        frame_dirs = frame_dirs[:1]
    for frame_dir in frame_dirs:
        cp = _get_chain_pattern(frame_dir)
        for base in (f"{frame_dir.name}.pd_h.pdb", f"{frame_dir.name}.pdb"):
            for csv_name, dest, col in (
                ("Water_Mediated", water_id, "Water Identity"),
                ("Metal_Mediated", metal_id, "Metal Identity"),
            ):
                csv_path = frame_dir / f"{base}_{cp}_{csv_name}.csv"
                if not csv_path.is_file():
                    continue
                try:
                    with open(csv_path, "r", encoding="utf-8", newline="") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            tok = _get_row_value(row, col)
                            if not tok:
                                continue
                            p = _parse_cocomaps_identity_token(tok)
                            if p:
                                dest.add(p)
                except OSError:
                    continue
    return water_id, metal_id


def _collect_mediated_identities(
    system_path: Path,
    *,
    first_frame_only: bool = False,
) -> Tuple[Set[Tuple[str, int, str]], Set[Tuple[str, int, str]]]:
    """
    Collect Water/Metal Identity tokens from mediated-interaction CSVs.

    When *first_frame_only* is True, only frame 1 rows from the aggregate CSVs
    (or per-frame ``frame_1/`` CSVs) are included.  Otherwise all frames are
    unioned.
    """
    water_id: Set[Tuple[str, int, str]] = set()
    metal_id: Set[Tuple[str, int, str]] = set()
    wa = system_path / "_water_mediated.csv"
    ma = system_path / "_metal_mediated.csv"

    ff = 1 if first_frame_only else None

    if wa.is_file():
        rows = _read_aggregate_mediated_csv(wa)
        _add_identities_from_mediated_aggregate_rows(
            rows, "Water Identity", water_id, frame_filter=ff
        )
    if ma.is_file():
        rows = _read_aggregate_mediated_csv(ma)
        _add_identities_from_mediated_aggregate_rows(
            rows, "Metal Identity", metal_id, frame_filter=ff
        )

    need_water_fb = not wa.is_file() or not water_id
    need_metal_fb = not ma.is_file() or not metal_id
    if need_water_fb or need_metal_fb:
        w_fb, m_fb = _collect_mediated_identities_from_frame_folders(
            system_path, first_frame_only=first_frame_only
        )
        if need_water_fb:
            water_id |= w_fb
        if need_metal_fb:
            metal_id |= m_fb

    return water_id, metal_id


def _extract_pdb_lines_for_residue(pdb_path: Path, chain: str, resnum: int) -> list[str]:
    """Extract ATOM/HETATM lines for a specific (chain, resnum) from a PDB file."""
    lines: list[str] = []
    with open(pdb_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            record = line[:6].strip()
            if record not in ("ATOM", "HETATM"):
                continue
            line_chain = line[21:22].strip()
            try:
                line_resnum = int(line[22:26].strip())
            except ValueError:
                continue
            if line_chain == chain and line_resnum == resnum:
                lines.append(line)
    return lines


def _extract_mediated_atom_lines(
    system_path: Path,
    water_idents: Set[Tuple[str, int, str]],
    metal_idents: Set[Tuple[str, int, str]],
    *,
    first_frame_only: bool = False,
    verbose: bool = False,
) -> Tuple[list[str], Set[Tuple[str, int]]]:
    """
    Extract ATOM/HETATM PDB lines for mediated waters/metals/ions from
    trimmed-frame PDBs.

    When *first_frame_only* is True only the first frame directory is checked.

    Returns (pdb_lines, extracted_keys) where extracted_keys contains
    (chain, resnum) pairs that were successfully extracted.
    """
    pdb_lines: list[str] = []
    extracted_keys: Set[Tuple[str, int]] = set()

    pending_w = set(water_idents)
    pending_m = set(metal_idents)

    frame_dirs = _sorted_frame_dirs(system_path)
    if first_frame_only:
        frame_dirs = frame_dirs[:1]

    for fd in frame_dirs:
        if not pending_w and not pending_m:
            break
        tp = _find_trimmed_frame_pdb(fd)
        if tp is None or not tp.is_file():
            continue

        resolved_w: list[Tuple[str, int, str]] = []
        for ident in list(pending_w):
            ch, rn, rname = ident
            key = (ch, rn)
            if key in extracted_keys:
                resolved_w.append(ident)
                continue
            lines = _extract_pdb_lines_for_residue(tp, ch, rn)
            if lines:
                pdb_lines.extend(lines)
                extracted_keys.add(key)
                resolved_w.append(ident)
        for ident in resolved_w:
            pending_w.discard(ident)

        resolved_m: list[Tuple[str, int, str]] = []
        for ident in list(pending_m):
            ch, rn, rname = ident
            key = (ch, rn)
            if key in extracted_keys:
                resolved_m.append(ident)
                continue
            lines = _extract_pdb_lines_for_residue(tp, ch, rn)
            if lines:
                pdb_lines.extend(lines)
                extracted_keys.add(key)
                resolved_m.append(ident)
        for ident in resolved_m:
            pending_m.discard(ident)

    if verbose and pending_w:
        print(
            f"[viewer_pdb] warn: {len(pending_w)} water identity/identities "
            "not found in trimmed frame PDB(s)"
        )
    if verbose and pending_m:
        print(
            f"[viewer_pdb] warn: {len(pending_m)} metal identity/identities "
            "not found in trimmed frame PDB(s)"
        )

    return pdb_lines, extracted_keys


def _select_trimmed_residue(u: mda.Universe, chain: str, resnum: int):
    """Select residue in trimmed PDB; chain may be segid or chainID."""
    for sel in (
        f"chainID {chain} and resid {resnum}",
        f"segid {chain} and resid {resnum}",
    ):
        try:
            ag = u.select_atoms(sel)
            if len(ag):
                return ag
        except Exception:
            continue
    if not chain:
        try:
            ag = u.select_atoms(f"resid {resnum}")
            if len(ag):
                return ag
        except Exception:
            pass
    return u.atoms[:0]


def _trimmed_reference_position(ag, prefer_water_oxygen: bool) -> Optional[np.ndarray]:
    if len(ag) == 0:
        return None
    if prefer_water_oxygen:
        ow = ag.select_atoms("name OW or name OH2 or name O*")
        if len(ow):
            return np.asarray(ow[0].position, dtype=float)
    return np.asarray(ag.center_of_mass(), dtype=float)


def _build_original_water_reference_cache(orig_u: mda.Universe) -> list[Tuple[Tuple[str, int], np.ndarray]]:
    """(chain,resid) key and reference position (OW or COM) for each water residue."""
    out: list[Tuple[Tuple[str, int], np.ndarray]] = []
    for res in orig_u.residues:
        if not _is_water_resname(res.resname):
            continue
        ow = res.atoms.select_atoms("name OW or name OH2 or name O*")
        if len(ow):
            p = np.asarray(ow[0].position, dtype=float)
        else:
            p = np.asarray(res.atoms.center_of_mass(), dtype=float)
        out.append((_residue_key(res.atoms[0]), p))
    return out


def _nearest_water_key_from_cache(
    cache: list[Tuple[Tuple[str, int], np.ndarray]], target_pos: np.ndarray, cutoff_angstrom: float
) -> Optional[Tuple[str, int]]:
    best_d = float("inf")
    best_key = None
    for key, p in cache:
        d = float(np.linalg.norm(p - target_pos))
        if d < best_d and d <= cutoff_angstrom:
            best_d = d
            best_key = key
    return best_key


def _nearest_named_residue_key_in_original(
    orig_u: mda.Universe,
    target_pos: np.ndarray,
    resname_expected: str,
    cutoff_angstrom: float,
) -> Optional[Tuple[str, int]]:
    rup = str(resname_expected).strip().upper()
    best_d = float("inf")
    best_key = None
    for res in orig_u.residues:
        if str(res.resname).strip().upper() != rup:
            continue
        p = np.asarray(res.atoms.center_of_mass(), dtype=float)
        d = float(np.linalg.norm(p - target_pos))
        if d < best_d and d <= cutoff_angstrom:
            best_d = d
            best_key = _residue_key(res.atoms[0])
    return best_key


def _map_mediated_identities_to_original_keys(
    orig_u: mda.Universe,
    system_path: Path,
    water_idents: Set[Tuple[str, int, str]],
    metal_idents: Set[Tuple[str, int, str]],
    *,
    cutoff_angstrom: float = 2.0,
    verbose: bool = False,
) -> Tuple[Set[Tuple[str, int]], Set[Tuple[str, int]], Set[Tuple[str, int]]]:
    """
    Map CoCoMaps (trimmed) identities to original (chain, resid) using 3D proximity.
    For each identity, use the **first** trimmed frame (in order) where that residue
    appears, then match to the original **first-frame** structure. One Universe load
    per output frame.
    """
    wk: Set[Tuple[str, int]] = set()
    mk: Set[Tuple[str, int]] = set()
    ik: Set[Tuple[str, int]] = set()
    frame_dirs = _sorted_frame_dirs(system_path)
    if not frame_dirs:
        return wk, mk, ik

    water_cache = _build_original_water_reference_cache(orig_u)
    pending_w = set(water_idents)
    pending_m = set(metal_idents)

    for fd in frame_dirs:
        if not pending_w and not pending_m:
            break
        tp = _find_trimmed_frame_pdb(fd)
        if tp is None or not tp.is_file():
            continue
        u_t = None
        try:
            u_t = mda.Universe(str(tp))
            resolved_w: list[Tuple[str, int, str]] = []
            for ident in list(pending_w):
                ch, rn, rname = ident
                ag = _select_trimmed_residue(u_t, ch, rn)
                pos = _trimmed_reference_position(ag, prefer_water_oxygen=True)
                if pos is None:
                    continue
                k = _nearest_water_key_from_cache(water_cache, pos, cutoff_angstrom)
                if k:
                    wk.add(k)
                elif verbose:
                    print(f"[viewer_pdb] warn: no original water near trimmed {ch}:{rn} {rname}")
                resolved_w.append(ident)
            for ident in resolved_w:
                pending_w.discard(ident)

            resolved_m: list[Tuple[str, int, str]] = []
            for ident in list(pending_m):
                ch, rn, rname = ident
                ag = _select_trimmed_residue(u_t, ch, rn)
                pos = _trimmed_reference_position(ag, prefer_water_oxygen=False)
                if pos is None:
                    continue
                k = _nearest_named_residue_key_in_original(orig_u, pos, rname, cutoff_angstrom)
                if k:
                    ru = str(rname).strip().upper()
                    if ru in _METAL_UPPER:
                        mk.add(k)
                    elif ru in _ION_UPPER:
                        ik.add(k)
                    elif ru in WATER_RESNAMES:
                        wk.add(k)
                    else:
                        mk.add(k)
                elif verbose:
                    print(f"[viewer_pdb] warn: no original {rname} near trimmed {ch}:{rn}")
                resolved_m.append(ident)
            for ident in resolved_m:
                pending_m.discard(ident)
        except Exception:
            continue
        finally:
            if u_t is not None:
                try:
                    u_t.trajectory.close()
                except Exception:
                    pass

    if verbose and pending_w:
        print(
            f"[viewer_pdb] warn: {len(pending_w)} water identity/identities "
            "never appeared in any trimmed frame PDB"
        )
    if verbose and pending_m:
        print(
            f"[viewer_pdb] warn: {len(pending_m)} metal identity/identities "
            "never appeared in any trimmed frame PDB"
        )

    return wk, mk, ik


def _is_water_resname(resname: str) -> bool:
    return str(resname).strip().upper() in WATER_RESNAMES


def _is_metal_resname(resname: str) -> bool:
    return str(resname).strip().upper() in _METAL_UPPER


def _is_ion_resname(resname: str) -> bool:
    return str(resname).strip().upper() in _ION_UPPER


def write_viewer_frame_pdb(
    system_dir: os.PathLike,
    *,
    start_frame: int = 0,
    end_frame: int = -1,
    frame_step: int = 1,
    verbose: bool = False,
) -> bool:
    """
    Write ``frame_1/frame_1_viewer.pdb`` containing:

    * All chains (protein / DNA / ligand) from the first processed frame of the
      original uploaded PDB.
    * Mediated waters / metals / ions that appear in frame 1 interaction data,
      with coordinates from the frame 1 trimmed PDB.

    Returns True if the viewer PDB was written, False if skipped.
    """
    system_path = Path(system_dir)
    interactions_path = system_path / "_interactions.csv"
    if not interactions_path.is_file():
        if verbose:
            print("[viewer_pdb] No _interactions.csv; skip viewer PDB")
        return False

    original = _find_original_pdb(system_path)
    if not original or not original.is_file():
        if verbose:
            print("[viewer_pdb] No original PDB at system root; skip viewer PDB")
        return False

    wid, mid = _collect_mediated_identities(
        system_path, first_frame_only=True
    )

    raw_frames = _parse_raw_frames(original)
    num_frames = len(raw_frames)
    if num_frames == 0:
        if verbose:
            print("[viewer_pdb] No frames in original PDB; skip")
        return False

    end = end_frame if end_frame != -1 and end_frame <= num_frames else num_frames
    if start_frame < 0:
        start_frame = 0
    frame_step = max(1, frame_step)
    frames_to_process = list(range(start_frame, end, frame_step))
    if not frames_to_process:
        if verbose:
            print("[viewer_pdb] Empty frame range; skip")
        return False

    first_raw_idx = frames_to_process[0]
    raw_text = raw_frames[first_raw_idx]

    mediated_lines, _mediated_keys = _extract_mediated_atom_lines(
        system_path,
        wid,
        mid,
        first_frame_only=True,
        verbose=verbose,
    )

    tmp = tempfile.NamedTemporaryFile(suffix=".pdb", delete=False, mode="w", encoding="utf-8")
    tmp_path = tmp.name
    universe = None
    try:
        tmp.write(raw_text)
        if not raw_text.rstrip().endswith("END"):
            tmp.write("END\n")
        tmp.close()

        universe = mda.Universe(tmp_path)

        groups = []
        for residue in universe.residues:
            rname = residue.resname
            if _is_water_resname(rname) or _is_metal_resname(rname) or _is_ion_resname(rname):
                continue
            groups.append(residue.atoms)

        if not groups and not mediated_lines:
            return False

        out_dir = system_path / "frame_1"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "frame_1_viewer.pdb"

        if groups:
            combined = universe.atoms[:0]
            for ag in groups:
                combined += ag
            combined.write(str(out_path))

            if mediated_lines:
                with open(out_path, "r", encoding="utf-8") as f:
                    content = f.read()
                stripped = content.rstrip()
                if stripped.endswith("END"):
                    stripped = stripped[:-3].rstrip()
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(stripped + "\n")
                    for line in mediated_lines:
                        f.write(line if line.endswith("\n") else line + "\n")
                    f.write("END\n")
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                for line in mediated_lines:
                    f.write(line if line.endswith("\n") else line + "\n")
                f.write("END\n")

        if verbose:
            print(f"[viewer_pdb] Wrote {out_path}")
        return True
    finally:
        if universe is not None:
            try:
                universe.trajectory.close()
            except Exception:
                pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
