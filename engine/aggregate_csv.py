"""
Aggregate per-frame CoCoMaps CSVs into system-level files.

Produces:
  - _interactions.csv      (one row per residue pair per frame)
  - _area.csv              (one row per frame: BSA data)
  - _trends.csv            (one row per frame: interaction type counts)
  - _atom_pairs.csv        (one row per atom pair: all residue pairs, all frames)
  - _water_mediated.csv    (concatenated Water_Mediated rows + frame; for viewer / deployment)
  - _metal_mediated.csv    (concatenated Metal_Mediated rows + frame)
  - _metadata.json         (totalFrames, chainPattern, etc.)

Used by analyze_pdb.py (Step 5).
"""
import csv
import json
import re
from pathlib import Path
from typing import Optional, Union

from .job_id import ensure_job_fields

# Must match trend dicts built from summary_table and data.py TRENDS_KEYS order expectations.
_TREND_FRAME_KEYS = [
    "H-bonds", "Salt-bridges", "π-π interactions", "Cation-π interactions",
    "Anion-π interactions", "CH-O/N bonds", "CH-π interactions", "Halogen bonds",
    "Apolar vdW contacts", "Polar vdW contacts", "Proximal contacts", "Clashes",
    "Water mediated", "Metal mediated", "S-S bonds", "Amino-π interactions",
    "Lone pair-π interactions", "O/N/SH-π interactions",
]


def _normalize_csv_row_keys(row: dict) -> dict:
    """Strip BOM/whitespace from CSV DictReader keys."""
    out = {}
    for k, v in row.items():
        if k is None:
            continue
        nk = str(k).strip().lstrip("\ufeff")
        out[nk] = v
    return out


def _resolve_chain_letter(rk: dict, side: int) -> str:
    """
    CoCoMaps distance tables may use placeholders (e.g. @ / !) in Chain 1/2.
    Prefer Atom 1 org name / Atom 2 org name when those hold real chain letters.
    """
    if side == 1:
        c_raw = rk.get("Chain 1", "")
        org = rk.get("Atom 1 org name", "")
    else:
        c_raw = rk.get("Chain 2", "")
        org = rk.get("Atom 2 org name", "")
    c = str(c_raw).strip() if c_raw is not None else ""
    o = str(org).strip() if org is not None else ""
    if c in ("@", "!") or (len(c) == 1 and c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if len(o) == 1 and o.isalpha():
            return o.upper()
    if len(c) == 1 and c.isalpha():
        return c.upper()
    return c


def _infer_chain_pattern_from_distance_csv(path: Path) -> Optional[str]:
    """Return e.g. 'A_B' from first readable row of full.csv / trial24.csv."""
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rk = _normalize_csv_row_keys(row)
                c1 = _resolve_chain_letter(rk, 1)
                c2 = _resolve_chain_letter(rk, 2)
                if c1 and c2 and len(c1) == 1 and len(c2) == 1:
                    return f"{c1}_{c2}"
    except OSError:
        pass
    return None


def _distance_table_fallback_path(frame_folder: Path) -> Optional[Path]:
    """Intermediate CoCoMaps dumps when final_file.csv is not written yet."""
    for name in ("full.csv", "trial24.csv"):
        p = frame_folder / name
        if p.is_file():
            return p
    return None


def _extract_first_number(value_str):
    """Extract first numeric value from strings like '2331.8 / 1165.9' or '25.35%'"""
    if not value_str:
        return None
    slash_match = re.match(r'\s*([0-9]+(?:\.[0-9]+)?)\s*/', value_str)
    if slash_match:
        return slash_match.group(1)
    number_match = re.search(r'([0-9]+(?:\.[0-9]+)?)', value_str)
    return number_match.group(1) if number_match else None


def _get_chain_pattern(frame_folder: Path) -> str:
    """Detect chain pattern (e.g. 'A_B') from CSV files in frame folder."""
    pattern = re.compile(r'\.pd[b_h\.]*_([A-Z])_([A-Z])_final_file\.csv$')
    for f in frame_folder.iterdir():
        if f.is_file():
            match = pattern.search(f.name)
            if match:
                return f"{match.group(1)}_{match.group(2)}"
    fb = _distance_table_fallback_path(frame_folder)
    if fb:
        inferred = _infer_chain_pattern_from_distance_csv(fb)
        if inferred:
            return inferred
    return "A_B"


def _normalize_interaction_type(type_label):
    """Map equivalent interaction labels to canonical value (matches data.py)."""
    if not type_label:
        return None
    clean_label = type_label.strip()
    lower_label = clean_label.lower()
    if 'h-bond' in lower_label or 'hydrogen bond' in lower_label:
        return 'H-bond'
    elif 'salt-bridge' in lower_label or 'salt bridge' in lower_label:
        return 'Salt-bridge'
    elif 'π-π' in clean_label or 'pi-pi' in lower_label or 'pi pi' in lower_label:
        return 'π-π interactions'
    elif 'cation-π' in lower_label or 'cation-pi' in lower_label or 'cation_pi' in lower_label:
        return 'Cation-π interactions'
    elif 'anion-π' in lower_label or 'anion-pi' in lower_label or 'anion_pi' in lower_label:
        return 'Anion-π interactions'
    elif 'ch-o/n' in lower_label or 'c-h_on' in lower_label or 'c-h on' in lower_label or 'ch-on' in lower_label:
        return 'CH-O/N bonds'
    elif 'ch-π' in lower_label or 'ch-pi' in lower_label or 'c-h_pi' in lower_label or 'ch-π interaction' in lower_label:
        return 'CH-π interactions'
    elif 'halogen' in lower_label:
        return 'Halogen bonds'
    elif 'apolar vdw' in lower_label or 'apolar_vdw' in lower_label:
        return 'Apolar vdW contacts'
    elif 'polar vdw' in lower_label or 'polar_vdw' in lower_label:
        return 'Polar vdW contacts'
    elif 'proximal' in lower_label:
        return 'Proximal contacts'
    elif 'clash' in lower_label:
        return 'Clashes'
    elif 'metal mediated' in lower_label or 'metal_mediated' in lower_label or 'metal-mediated' in lower_label:
        return 'Metal-mediated contacts'
    elif 'n-s-o-h' in lower_label or 'n-s-o-h_pi' in lower_label or 'o/n/sh' in lower_label or 'ons-oh-pi' in lower_label:
        return 'O/N/SH-π interactions'
    elif 'lone pair' in lower_label or 'lone_pair' in lower_label or 'lp-π' in lower_label or 'lp-pi' in lower_label:
        return 'lp-π interactions'
    elif 'water mediated' in lower_label or 'water_mediated' in lower_label or 'water-mediated' in lower_label:
        return 'Water-mediated contacts'
    elif 's-s bond' in lower_label or 'ss bond' in lower_label or 'ss_bond' in lower_label or 's-s' in lower_label:
        return 'S-S bond'
    elif 'amino-pi' in lower_label or 'amino_pi' in lower_label or 'polar-π' in lower_label or 'polar-pi' in lower_label:
        return 'Amino-π interactions'
    return clean_label


def _get_final_file(frame_folder: Path, chain_pattern: str) -> Optional[Path]:
    """Return path to final_file.csv for frame, or None."""
    for base in [f"{frame_folder.name}.pd_h.pdb", f"{frame_folder.name}.pdb"]:
        p = frame_folder / f"{base}_{chain_pattern}_final_file.csv"
        if p.exists():
            return p
    return None


def _get_rsa_stats_file(frame_folder: Path, chain_pattern: str) -> Optional[Path]:
    """Return path to Rsa_stats.csv for frame, or None."""
    for base in [f"{frame_folder.name}.pd_h.pdb", f"{frame_folder.name}.pdb"]:
        p = frame_folder / f"{base}_{chain_pattern}_complex.pdb_Rsa_stats.csv"
        if p.exists():
            return p
    return None


def _get_summary_table_file(frame_folder: Path, chain_pattern: str) -> Optional[Path]:
    """Return path to summary_table.csv for frame, or None."""
    for base in [f"{frame_folder.name}.pd_h.pdb", f"{frame_folder.name}.pdb"]:
        p = frame_folder / f"{base}_{chain_pattern}_summary_table.csv"
        if p.exists():
            return p
    return None


# CSV filename -> normalized interaction type (for atom-pairs aggregation)
_CSV_TO_INTERACTION_TYPE = {
    'H-bond': 'H-bond',
    'Salt_bridge': 'Salt-bridge',
    'pi-pi': 'π-π interactions',
    'Cation_pi': 'Cation-π interactions',
    'Anion_pi': 'Anion-π interactions',
    'C-H_ON': 'CH-O/N bonds',
    'C-H_pi': 'CH-π interactions',
    'Halogen_bond': 'Halogen bonds',
    'Apolar_vdw': 'Apolar vdW contacts',
    'Polar_vdw': 'Polar vdW contacts',
    'Proximal': 'Proximal contacts',
    'Clash': 'Clashes',
    'Metal_Mediated': 'Metal-mediated contacts',
    'N-S-O-H_pi': 'O/N/SH-π interactions',
    'Lone_pair_pi': 'lp-π interactions',
    'Water_Mediated': 'Water-mediated contacts',
    'SS_bond': 'S-S bond',
    'Amino_pi': 'Amino-π interactions',
}

_INTERACTION_CSV_NAMES = list(_CSV_TO_INTERACTION_TYPE.keys())


def _extract_atom_pair_from_row(row: dict, interaction_type: str) -> Optional[tuple]:
    """
    Extract (atom1, atom2, distance, angle) from a type-specific CSV row.
    Returns None if extraction fails.
    """
    if not all(k in row for k in ['Res. Name 1', 'Res. Number 1', 'Chain 1',
                                  'Res. Name 2', 'Res. Number 2', 'Chain 2']):
        return None

    is_pi = 'π' in interaction_type or 'pi' in interaction_type.lower()
    row_res_name1 = str(row.get('Res. Name 1', '')).strip()
    row_res_num1 = str(row.get('Res. Number 1', ''))
    row_chain1 = str(row.get('Chain 1', '')).strip()
    row_res_name2 = str(row.get('Res. Name 2', '')).strip()
    row_res_num2 = str(row.get('Res. Number 2', ''))
    row_chain2 = str(row.get('Chain 2', '')).strip()

    if is_pi:
        is_pi_pi = interaction_type.lower().count('pi') >= 2 or 'π-π' in interaction_type
        is_ch_pi = ('ch' in interaction_type.lower() or 'c-h' in interaction_type.lower()) and not is_pi_pi
        is_cation_pi = 'cation' in interaction_type.lower()
        is_anion_pi = 'anion' in interaction_type.lower()
        is_lp_pi = 'lp' in interaction_type.lower() or 'lone' in interaction_type.lower()
        is_amino_pi = 'amino' in interaction_type.lower() or 'polar' in interaction_type.lower()
        is_ons_h_pi = 'o/n/s' in interaction_type.lower() or 'n-s-o-h' in interaction_type.lower()

        ring_from = row.get('Ring From', '').strip()

        def is_ring(res_name, res_num, chain):
            if not ring_from:
                return False
            return f"{res_name}-{res_num}" in ring_from or f"{chain}-{res_num}" in ring_from

        res1_ring = is_ring(row_res_name1, row_res_num1, row_chain1)
        res2_ring = is_ring(row_res_name2, row_res_num2, row_chain2)
        if not res1_ring and not res2_ring and ring_from:
            if row_res_num1 in ring_from:
                res1_ring = True
            elif row_res_num2 in ring_from:
                res2_ring = True

        if is_pi_pi:
            atom1, atom2 = "Pi-Ring", "Pi-Ring"
        elif is_ch_pi or is_ons_h_pi:
            c_atom = row.get('C Atom', '').strip()
            h_atom = row.get('H Atom', '').strip()
            ch_label = f"{c_atom}({h_atom})" if c_atom and h_atom else (c_atom or "CH")
            atom1, atom2 = ch_label, "Pi-Ring"
        elif is_cation_pi:
            cation_atom = row.get('Cation Atom', '').strip()
            atom1, atom2 = (cation_atom or "Cation"), "Pi-Ring"
        elif is_anion_pi:
            anion_atom = row.get('Anion Atom', '').strip()
            atom1, atom2 = (anion_atom or "Anion"), "Pi-Ring"
        elif is_lp_pi:
            lp_atom = row.get('Lone_pair Atom', '').strip()
            atom1, atom2 = (lp_atom or "Lone_pair"), "Pi-Ring"
        elif is_amino_pi:
            polar_atom = row.get('Polar Atom', '').strip()
            atom1, atom2 = (polar_atom or "Polar"), "Pi-Ring"
        else:
            atom1 = row.get('Atom 1', '').strip() or "Partner"
            atom2 = "Pi-Ring"
    else:
        atom1 = row.get('Atom 1', '').strip()
        atom2 = row.get('Atom 2', '').strip()

    if not atom1 or not atom2:
        return None

    distance = None
    for col in ['Distance (Å)', 'Distance', 'Distance(Å)', 'Dist (Å)', 'Dist', 'distance',
                'Centroid Distance', 'Centroid Distance (Å)', 'Ring Distance', 'Ring Distance (Å)']:
        if col in row and row[col]:
            try:
                distance = float(str(row[col]).replace('*', '').strip())
            except ValueError:
                pass
            break

    angle = None
    if 'DHA Angle' in row and row['DHA Angle']:
        try:
            angle = float(str(row['DHA Angle']).strip())
        except ValueError:
            pass

    return (atom1, atom2, distance, angle)


# Mapping from summary_table Property name to trends key
_TRENDS_PROPERTY_MAP = {
    'H-bonds': 'H-bonds',
    'Salt-bridges': 'Salt-bridges',
    'π-π interactions': 'π-π interactions',
    'Cation-π': 'Cation-π interactions',
    'Anion-π': 'Anion-π interactions',
    'CH-O/N bonds': 'CH-O/N bonds',
    'CH-π interactions': 'CH-π interactions',
    'Halogen bonds': 'Halogen bonds',
    'Apolar vdW': 'Apolar vdW contacts',
    'Polar vdW': 'Polar vdW contacts',
    'Proximal contacts': 'Proximal contacts',
    'Clashes': 'Clashes',
    # Must match keys in trend_vals (same names as backend TRENDS_KEYS / frontend trendLabel).
    # Previously pointed at 'Water-mediated contacts' / 'Metal-mediated contacts', which are
    # not in trend_vals, so counts were always left at zero.
    'Water mediated': 'Water mediated',
    'Metal mediated': 'Metal mediated',
    # Summary tables often use hyphens (e.g. "Water-Mediated Contacts")
    'water-mediated': 'Water mediated',
    'metal-mediated': 'Metal mediated',
    'S-S': 'S-S bonds',
    'SS bond': 'S-S bonds',
    'Amino-π': 'Amino-π interactions',
    'Polar-π (Amino-π)': 'Amino-π interactions',
    'lp-π': 'Lone pair-π interactions',
    'Lone pair-π': 'Lone pair-π interactions',
    'O/N/SH-π': 'O/N/SH-π interactions',
}


def _read_mediated_type_csv(
    frame_folder: Path,
    chain_pattern: str,
    frame_num: int,
    csv_suffix: str,
) -> list[dict]:
    """Read one Water_Mediated or Metal_Mediated CSV; rows get a ``frame`` column."""
    rows: list[dict] = []
    for base in [f"{frame_folder.name}.pd_h.pdb", f"{frame_folder.name}.pdb"]:
        path = frame_folder / f"{base}_{chain_pattern}_{csv_suffix}.csv"
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                cols = list(reader.fieldnames or [])
                for row in reader:
                    rec = {"frame": frame_num}
                    for c in cols:
                        if c is None:
                            continue
                        key = c.strip()
                        rec[key] = row.get(c, "")
                    rows.append(rec)
        except OSError:
            continue
        break
    return rows


def _fieldnames_for_mediated_rows(rows: list[dict]) -> list[str]:
    if not rows:
        return ["frame"]
    ordered: list[str] = []
    for r in rows:
        for k in r:
            if k not in ordered:
                ordered.append(k)
    if "frame" in ordered:
        ordered.remove("frame")
    return ["frame"] + ordered


def _aggregate_from_distance_table_fallback(
    path: Path,
    frame_num: int,
    interactions_rows: list,
    atom_pairs_rows: list,
    trends_rows: list,
    area_rows: list,
    verbose: bool,
) -> None:
    """
    Build interaction / atom-pair / trend rows from CoCoMaps intermediate ``full.csv``
    or ``trial24.csv`` when ``*_final_file.csv`` was not produced.

    Interaction typing is not available in these files; all contacts are recorded as
    **Proximal contacts** (within-cutoff distance pairs). BSA/trend charts that need
    NACCESS / summary_table still get zeros unless those files exist.
    """
    proximal = "Proximal contacts"
    seen_pairs = set()

    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rk = _normalize_csv_row_keys(row)
                c1 = _resolve_chain_letter(rk, 1)
                c2 = _resolve_chain_letter(rk, 2)
                rn1 = str(rk.get("Res. Name 1", "")).strip()
                rn2 = str(rk.get("Res. Name 2", "")).strip()
                try:
                    num1 = int(float(str(rk.get("Res. Number 1", "")).strip()))
                except (TypeError, ValueError):
                    continue
                try:
                    num2 = int(float(str(rk.get("Res. Number 2", "")).strip()))
                except (TypeError, ValueError):
                    continue
                if not (c1 and c2 and rn1 and rn2):
                    continue

                pair_key = (rn1, num1, c1, rn2, num2, c2)
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    interactions_rows.append({
                        "resName1": rn1,
                        "resNum1": str(num1),
                        "chain1": c1,
                        "resName2": rn2,
                        "resNum2": str(num2),
                        "chain2": c2,
                        "frame": frame_num,
                        "types": proximal,
                    })

                dist_raw = ""
                for dk in rk:
                    if dk and "Distance" in dk and "\u00c5" in dk:
                        dist_raw = rk.get(dk, "")
                        break
                if dist_raw == "":
                    dist_raw = rk.get("Distance", "") or ""
                atom_pairs_rows.append({
                    "resName1": rn1,
                    "resNum1": str(num1),
                    "chain1": c1,
                    "resName2": rn2,
                    "resNum2": str(num2),
                    "chain2": c2,
                    "frame": frame_num,
                    "interactionType": proximal,
                    "atom1": str(rk.get("Atom 1", "")).strip() or "-",
                    "atom2": str(rk.get("Atom 2", "")).strip() or "-",
                    "distance": str(dist_raw).strip(),
                    "angle": "",
                })
    except OSError as e:
        if verbose:
            print(f"  [aggregate] Could not read distance fallback {path}: {e}")
        return

    if not any(r.get("frame") == frame_num for r in trends_rows):
        trend_vals = {k: 0 for k in _TREND_FRAME_KEYS}
        trend_vals["Proximal contacts"] = len(seen_pairs)
        trends_rows.append({"frame": frame_num, **trend_vals})

    if not any(r.get("frame") == frame_num for r in area_rows):
        area_rows.append({
            "frame": frame_num,
            "totalBSA": 0.0,
            "polarBSA": 0.0,
            "nonPolarBSA": 0.0,
            "totalPercent": 0.0,
            "polarPercent": 0.0,
            "nonPolarPercent": 0.0,
        })

    if verbose:
        print(
            f"  [aggregate] Used distance-table fallback {path.name} for frame {frame_num}: "
            f"{len(seen_pairs)} residue pairs, {proximal} only (full CoCoMaps final_file not found)."
        )


def aggregate_system(system_path: Union[str, Path], verbose: bool = True) -> bool:
    """
    Aggregate per-frame CSVs into system-level _interactions.csv, _area.csv,
    _trends.csv, _atom_pairs.csv, _water_mediated.csv, _metal_mediated.csv,
    and _metadata.json.

    Returns True if any files were written, False if nothing to aggregate.
    """
    system_path = Path(system_path)
    if not system_path.is_dir():
        return False

    frame_folders = sorted(
        [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')],
        key=lambda f: int(f.name.split('_')[1]) if '_' in f.name else 0,
    )

    if not frame_folders:
        return False

    chain_pattern = _get_chain_pattern(frame_folders[0])
    total_frames = len(frame_folders)

    interactions_rows = []
    area_rows = []
    trends_rows = []
    atom_pairs_rows = []
    water_mediated_rows = []
    metal_mediated_rows = []

    for frame_folder in frame_folders:
        try:
            frame_num = int(frame_folder.name.split('_')[1])
        except (IndexError, ValueError):
            continue

        # --- Interactions from final_file.csv ---
        n_ix_before_frame = len(interactions_rows)
        final_file = _get_final_file(frame_folder, chain_pattern)
        if final_file:
            with open(final_file, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rk = _normalize_csv_row_keys(row)
                    c1 = (rk.get('Chain 1') or rk.get('Res. Chain 1') or '').strip()
                    c2 = (rk.get('Chain 2') or rk.get('Res. Chain 2') or '').strip()
                    if not all(rk.get(k) for k in ['Res. Name 1', 'Res. Number 1', 'Res. Name 2', 'Res. Number 2']):
                        continue
                    if not (c1 and c2):
                        continue
                    types_raw = rk.get('Type of Interactions', '') or ''
                    types_list = []
                    if types_raw:
                        for t in types_raw.split(';'):
                            nt = _normalize_interaction_type(t.strip())
                            if nt and nt not in types_list:
                                types_list.append(nt)
                    interactions_rows.append({
                        'resName1': rk['Res. Name 1'],
                        'resNum1': rk['Res. Number 1'],
                        'chain1': c1,
                        'resName2': rk['Res. Name 2'],
                        'resNum2': rk['Res. Number 2'],
                        'chain2': c2,
                        'frame': frame_num,
                        'types': ';'.join(types_list),
                    })

        # --- Area from Rsa_stats.csv ---
        rsa_file = _get_rsa_stats_file(frame_folder, chain_pattern)
        if rsa_file:
            total_bsa = polar_bsa = non_polar_bsa = 0.0
            total_percent = polar_percent = non_polar_percent = 0.0
            with open(rsa_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_idx_str = row.get('', '').strip()
                    try:
                        row_idx = int(row_idx_str)
                    except ValueError:
                        continue
                    val = row.get('Value', '')
                    match = _extract_first_number(val)
                    if not match:
                        continue
                    v = float(match)
                    if row_idx == 0:
                        total_bsa = v
                    elif row_idx == 1:
                        total_percent = v
                    elif row_idx == 2:
                        polar_bsa = v
                    elif row_idx == 3:
                        polar_percent = v
                    elif row_idx == 4:
                        non_polar_bsa = v
                    elif row_idx == 5:
                        non_polar_percent = v
            area_rows.append({
                'frame': frame_num,
                'totalBSA': total_bsa,
                'polarBSA': polar_bsa,
                'nonPolarBSA': non_polar_bsa,
                'totalPercent': total_percent,
                'polarPercent': polar_percent,
                'nonPolarPercent': non_polar_percent,
            })

        # --- Trends from summary_table.csv ---
        summary_file = _get_summary_table_file(frame_folder, chain_pattern)
        if summary_file:
            trend_vals = {k: 0 for k in _TREND_FRAME_KEYS}
            with open(summary_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    prop = row.get('Property', '')
                    try:
                        val = int(row.get('Value', 0))
                    except (TypeError, ValueError):
                        val = 0
                    prop_lower = prop.lower()
                    for key, trend_key in _TRENDS_PROPERTY_MAP.items():
                        if trend_key not in trend_vals:
                            continue
                        if key.lower() in prop_lower:
                            trend_vals[trend_key] = val
                            break
            trends_rows.append({'frame': frame_num, **trend_vals})

        # --- Atom pairs from type-specific CSVs ---
        for csv_name in _INTERACTION_CSV_NAMES:
            interaction_type = _CSV_TO_INTERACTION_TYPE[csv_name]
            csv_file = None
            for base in [f"{frame_folder.name}.pd_h.pdb", f"{frame_folder.name}.pdb"]:
                p = frame_folder / f"{base}_{chain_pattern}_{csv_name}.csv"
                if p.exists():
                    csv_file = p
                    break
            if not csv_file:
                continue

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = _extract_atom_pair_from_row(row, interaction_type)
                    if result:
                        atom1, atom2, distance, angle = result
                        atom_pairs_rows.append({
                            'resName1': row['Res. Name 1'],
                            'resNum1': row['Res. Number 1'],
                            'chain1': row['Chain 1'],
                            'resName2': row['Res. Name 2'],
                            'resNum2': row['Res. Number 2'],
                            'chain2': row['Chain 2'],
                            'frame': frame_num,
                            'interactionType': interaction_type,
                            'atom1': atom1,
                            'atom2': atom2,
                            'distance': '' if distance is None else str(distance),
                            'angle': '' if angle is None else str(angle),
                        })

        # --- Water_Mediated / Metal_Mediated (full rows for viewer + deployment) ---
        water_mediated_rows.extend(
            _read_mediated_type_csv(frame_folder, chain_pattern, frame_num, "Water_Mediated")
        )
        metal_mediated_rows.extend(
            _read_mediated_type_csv(frame_folder, chain_pattern, frame_num, "Metal_Mediated")
        )

        # CoCoMaps sometimes leaves only full.csv / trial24.csv (distance table) when the
        # pipeline does not write *_final_file.csv. Approximate residue/atom data from that.
        if len(interactions_rows) == n_ix_before_frame:
            fb = _distance_table_fallback_path(frame_folder)
            if fb:
                _aggregate_from_distance_table_fallback(
                    fb, frame_num, interactions_rows, atom_pairs_rows,
                    trends_rows, area_rows, verbose,
                )

    # Pad area/trends so every frame has a row (zeros if NACCESS/summary missing).
    frame_nums_ordered = sorted(
        int(f.name.split('_')[1])
        for f in frame_folders
        if f.is_dir() and f.name.startswith('frame_') and '_' in f.name
    )
    have_area = {r['frame'] for r in area_rows}
    have_trend = {r['frame'] for r in trends_rows}
    for fn in frame_nums_ordered:
        if fn not in have_area:
            area_rows.append({
                'frame': fn,
                'totalBSA': 0.0,
                'polarBSA': 0.0,
                'nonPolarBSA': 0.0,
                'totalPercent': 0.0,
                'polarPercent': 0.0,
                'nonPolarPercent': 0.0,
            })
        if fn not in have_trend:
            trends_rows.append({'frame': fn, **{k: 0 for k in _TREND_FRAME_KEYS}})
    area_rows.sort(key=lambda r: int(r['frame']))
    trends_rows.sort(key=lambda r: int(r['frame']))

    # Write outputs
    wrote_any = False

    if interactions_rows:
        out_path = system_path / '_interactions.csv'
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'resName1', 'resNum1', 'chain1', 'resName2', 'resNum2', 'chain2', 'frame', 'types'
            ])
            writer.writeheader()
            writer.writerows(interactions_rows)
        wrote_any = True
        if verbose:
            print(f"  Wrote {out_path} ({len(interactions_rows)} rows)")

    if area_rows:
        out_path = system_path / '_area.csv'
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'frame', 'totalBSA', 'polarBSA', 'nonPolarBSA',
                'totalPercent', 'polarPercent', 'nonPolarPercent'
            ])
            writer.writeheader()
            writer.writerows(area_rows)
        wrote_any = True
        if verbose:
            print(f"  Wrote {out_path} ({len(area_rows)} rows)")

    if trends_rows:
        out_path = system_path / '_trends.csv'
        fieldnames = ['frame'] + [k for k in trends_rows[0].keys() if k != 'frame']
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trends_rows)
        wrote_any = True
        if verbose:
            print(f"  Wrote {out_path} ({len(trends_rows)} rows)")

    if atom_pairs_rows:
        out_path = system_path / '_atom_pairs.csv'
        fieldnames = [
            'resName1', 'resNum1', 'chain1', 'resName2', 'resNum2', 'chain2',
            'frame', 'interactionType', 'atom1', 'atom2', 'distance', 'angle'
        ]
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(atom_pairs_rows)
        wrote_any = True
        if verbose:
            print(f"  Wrote {out_path} ({len(atom_pairs_rows)} rows)")

    if water_mediated_rows:
        out_path = system_path / "_water_mediated.csv"
        wm_fields = _fieldnames_for_mediated_rows(water_mediated_rows)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=wm_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(water_mediated_rows)
        wrote_any = True
        if verbose:
            print(f"  Wrote {out_path} ({len(water_mediated_rows)} rows)")

    if metal_mediated_rows:
        out_path = system_path / "_metal_mediated.csv"
        mm_fields = _fieldnames_for_mediated_rows(metal_mediated_rows)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=mm_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(metal_mediated_rows)
        wrote_any = True
        if verbose:
            print(f"  Wrote {out_path} ({len(metal_mediated_rows)} rows)")

    metadata_path = system_path / '_metadata.json'

    existing = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                maybe = json.load(f)
            if isinstance(maybe, dict):
                existing = maybe
        except Exception:
            existing = {}

    # Always update these to reflect what we just aggregated.
    existing['totalFrames'] = total_frames
    existing['chainPattern'] = chain_pattern

    # Ensure a public job id exists (and regenerate if expired).
    ensure_job_fields(existing, days_valid=60, regenerate_if_expired=True)

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2)
    wrote_any = True
    if verbose:
        print(f"  Wrote {metadata_path}")

    return wrote_any
