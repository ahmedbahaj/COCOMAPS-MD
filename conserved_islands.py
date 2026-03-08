# conserved_islands.py
"""
Conserved island analysis for MD trajectories.

Detects groups of residues that stay clustered as connected components
across a high fraction of frames (conserved binding patches).
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import networkx as nx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_residue_names(system_dir: Path) -> dict[tuple, str]:
    """
    Build (chain, resNum) -> resName lookup by scanning all final_file.csv frames.
    Residues that only appear in later frames (e.g. A:9 in frame 2+) would otherwise be UNK.
    """
    csv_paths = _find_final_files(system_dir)
    if not csv_paths:
        return {}

    lookup: dict[tuple, str] = {}
    for csv_path in csv_paths:
        df = pd.read_csv(csv_path, low_memory=False)
        if df is None or df.empty:
            continue
        cols = {c.strip(): c for c in df.columns}
        pairs = [
            ("Res. Name 1", "Res. Number 1", cols.get("Chain 1") or cols.get("Res. Chain 1")),
            ("Res. Name 2", "Res. Number 2", cols.get("Chain 2") or cols.get("Res. Chain 2")),
        ]
        for res_name_key, res_num_key, chain_col in pairs:
            rn = cols.get(res_name_key)
            rnum = cols.get(res_num_key)
            if not (rn and rnum and chain_col):
                continue
            for _, row in df.iterrows():
                chain = str(row[chain_col]).strip() if pd.notna(row.get(chain_col)) else "?"
                res_num = row[rnum]
                res_name = str(row[rn]).strip() if pd.notna(row.get(rn)) else ""
                if not res_name:
                    continue
                key = (chain, res_num)
                if key not in lookup:
                    lookup[key] = res_name

    return lookup


def _detect_residue_columns(data: pd.DataFrame):
    """Detect residue number and chain column names. Returns (col_num1, col_num2, col_chain1, col_chain2) or None."""
    cols = {c.strip(): c for c in data.columns}
    if "Res. Number 1" in cols and "Res. Number 2" in cols:
        c1 = cols.get("Res. Chain 1") or cols.get("Chain 1")
        c2 = cols.get("Res. Chain 2") or cols.get("Chain 2")
        return ("Res. Number 1", "Res. Number 2", c1, c2)
    if "NA/Protein Res Number" in cols and "Ligand Res Number" in cols:
        ch1 = cols.get("NA/Protein Chain") or cols.get("RNA chain")
        ch2 = cols.get("Ligand Chain")
        return ("NA/Protein Res Number", "Ligand Res Number", ch1, ch2)
    if "RNA Res. Number" in cols and "Ligand Res. Number" in cols:
        ch1 = cols.get("RNA chain") or cols.get("RNA Chain")
        ch2 = cols.get("Ligand Chain")
        return ("RNA Res. Number", "Ligand Res. Number", ch1, ch2)
    return None


def _get_chain_pattern(frame_folder: Path) -> str:
    """Detect the chain pattern (e.g. 'A_B', 'A_C') from CSV files in a frame folder."""
    pattern = re.compile(r'\.pd[b_h\.]*_([A-Z])_([A-Z])_final_file\.csv$')
    for f in frame_folder.iterdir():
        if f.is_file():
            match = pattern.search(f.name)
            if match:
                return f"{match.group(1)}_{match.group(2)}"
    return "A_B"


def _find_final_files(system_dir: Path) -> list[Path]:
    """
    Discover all *_final_file.csv paths inside a system directory.

    Scans frame_N/ sub-folders in numeric order, auto-detects the chain
    pattern and the reduce / no-reduce naming convention.

    Returns:
        Sorted list of Path objects, one per frame that has a final_file.csv.
    """
    frame_folders = sorted(
        [f for f in system_dir.iterdir() if f.is_dir() and f.name.startswith("frame_")],
        key=lambda f: int(f.name.split("_")[1]) if "_" in f.name else 0,
    )

    csv_paths = []
    for frame_folder in frame_folders:
        chain_pattern = _get_chain_pattern(frame_folder)
        # Try reduce naming first, then standard
        csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_{chain_pattern}_final_file.csv"
        if not csv_file.exists():
            csv_file = frame_folder / f"{frame_folder.name}.pdb_{chain_pattern}_final_file.csv"
        if csv_file.exists():
            csv_paths.append(csv_file)

    return csv_paths


# ---------------------------------------------------------------------------
# Single-frame island detection (kept for backward compatibility)
# ---------------------------------------------------------------------------

def count_island_sizes(data, maxGroupSize=13, debug=False, log_file="island_debug.log") -> pd.DataFrame:
    """
    Build a graph from residue-residue interactions and return one row per island
    (connected component) with Island_id, Island_size, Residues, and Chains.
    """
    def log(msg):
        if debug:
            with open(log_file, "a") as f:
                f.write(str(msg) + "\n")

    if debug:
        open(log_file, "w").close()

    if data is None or data.empty:
        return pd.DataFrame(columns=["Island_id", "Island_size", "Residues", "Chains"])

    detected = _detect_residue_columns(data)
    if not detected:
        raise ValueError(
            "Could not find residue columns. Expected one of: "
            "'Res. Number 1' & 'Res. Number 2'; "
            "'NA/Protein Res Number' & 'Ligand Res Number'; "
            "'RNA Res. Number' & 'Ligand Res. Number'. "
            f"Found columns: {list(data.columns)}"
        )
    col_num1, col_num2, col_chain1, col_chain2 = detected

    G = nx.Graph()
    for _, row in data.iterrows():
        res_num1 = row[col_num1]
        res_num2 = row[col_num2]
        chain1 = str(row[col_chain1]).strip() if col_chain1 and pd.notna(row.get(col_chain1)) else "?"
        chain2 = str(row[col_chain2]).strip() if col_chain2 and pd.notna(row.get(col_chain2)) else "?"
        node1 = (chain1, res_num1)
        node2 = (chain2, res_num2)
        G.add_edge(node1, node2)
        if debug:
            log(f"  {chain1}:{res_num1} <--> {chain2}:{res_num2}")

    log(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    connected_components = list(nx.connected_components(G))
    log(f"Connected components: {len(connected_components)}")

    rows_out = []
    for island_id, component in enumerate(connected_components, 1):
        size = len(component)
        residues = sorted(component, key=lambda x: (str(x[0]), x[1]))
        residue_str = ", ".join(f"{ch}:{res}" for ch, res in residues)
        chains = sorted(set(ch for ch, _ in residues))
        chains_str = ", ".join(chains)
        rows_out.append({
            "Island_id": island_id,
            "Island_size": size,
            "Residues": residue_str,
            "Chains": chains_str,
        })
        log(f"Island {island_id} (size={size}): chains=[{chains_str}], residues=[{residue_str}]")

    islands_df = pd.DataFrame(rows_out)
    log(f"Islands DataFrame:\n{islands_df}")
    return islands_df


def process_final_files(
    path_list,
    output_csv_path=None,
    debug=False,
    log_file="island_debug.log",
) -> pd.DataFrame:
    """
    Process one or more final-file CSVs independently and produce a combined DataFrame.
    """
    if not path_list:
        raise ValueError("path_list must contain at least one path")

    all_rows = []
    for path in path_list:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Final file not found: {path}")
        df = pd.read_csv(p, low_memory=False)
        islands_df = count_island_sizes(df, debug=debug, log_file=log_file)
        for _, row in islands_df.iterrows():
            all_rows.append({
                "Input_file": str(p.resolve()),
                "Island_id": row["Island_id"],
                "Island_size": row["Island_size"],
                "Residues": row["Residues"],
                "Chains": row["Chains"],
            })

    result = pd.DataFrame(all_rows)
    if output_csv_path is not None:
        out = Path(output_csv_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(out, index=False)
    return result


# ---------------------------------------------------------------------------
# Multi-frame conserved island detection
# ---------------------------------------------------------------------------

def _build_frame_graph(csv_path: Path) -> Optional[nx.Graph]:
    """Read a single final_file.csv and return its interaction graph, or None on failure."""
    df = pd.read_csv(csv_path, low_memory=False)
    if df is None or df.empty:
        return None

    detected = _detect_residue_columns(df)
    if not detected:
        return None

    col_num1, col_num2, col_chain1, col_chain2 = detected

    G = nx.Graph()
    for _, row in df.iterrows():
        chain1 = str(row[col_chain1]).strip() if col_chain1 and pd.notna(row.get(col_chain1)) else "?"
        chain2 = str(row[col_chain2]).strip() if col_chain2 and pd.notna(row.get(col_chain2)) else "?"
        node1 = (chain1, row[col_num1])
        node2 = (chain2, row[col_num2])
        G.add_edge(node1, node2)

    return G


def count_conserved_islands(
    system_dir: Union[str, Path],
    min_consistency: float = 0.70,
    min_island_size: int = 3,
    debug: bool = False,
) -> tuple[list[dict], dict[frozenset, int], int]:
    """
    Find conserved islands as connected components of the *direct* A–B interaction graph.

    Island = largest paths of residues connected by direct interactions (A↔B only)
    that are conserved in >= min_consistency of frames. Every residue in an island
    has at least one direct conserved partner (so connectedTo is never empty).

    Algorithm:
        1. Count how many frames each direct A–B pair appears in (final_file edges).
        2. Build graph with only edges where count/total_frames >= min_consistency.
        3. Islands = connected components of this graph (each is an A–B–A–B… path).
        4. For each residue, connectedTo = neighbors in this graph.

    Returns:
        (islands_out, direct_pair_counts, total_frames)
    """
    system_dir = Path(system_dir)
    if not system_dir.is_dir():
        raise NotADirectoryError(f"System directory not found: {system_dir}")

    csv_paths = _find_final_files(system_dir)
    if not csv_paths:
        raise FileNotFoundError(f"No final_file.csv found in {system_dir}")

    total_frames = len(csv_paths)
    co_direct_edges: dict[frozenset, int] = defaultdict(int)

    for idx, csv_path in enumerate(csv_paths, 1):
        G = _build_frame_graph(csv_path)
        if G is None:
            continue
        if debug:
            print(f"  Frame {idx}/{total_frames}: {G.number_of_nodes()} nodes, "
                  f"{G.number_of_edges()} edges  ({csv_path.parent.name})")
        for u, v in G.edges():
            co_direct_edges[frozenset({u, v})] += 1

    # Graph with only direct A–B edges that meet the conservation threshold
    direct_conserved_G = nx.Graph()
    for pair, count in co_direct_edges.items():
        if count / total_frames >= min_consistency:
            n1, n2 = pair
            direct_conserved_G.add_edge(n1, n2, weight=count / total_frames)

    components = sorted(nx.connected_components(direct_conserved_G), key=len, reverse=True)
    islands_out = []
    island_id = 0
    for component in components:
        if len(component) < min_island_size:
            continue
        island_id += 1
        residues = sorted(component, key=lambda x: (str(x[0]), x[1]))
        residue_str = ", ".join(f"{ch}:{res}" for ch, res in residues)
        chains = sorted(set(ch for ch, _ in residues))
        chains_str = ", ".join(chains)
        islands_out.append({
            "Island_id": island_id,
            "Island_size": len(component),
            "Residues": residue_str,
            "Chains": chains_str,
            "component": component,
        })

    return islands_out, co_direct_edges, total_frames


def run_conserved_islands(
    output_dir: Union[str, Path],
    min_consistency: float = 0.70,
    min_island_size: int = 3,
    verbose: bool = True,
    step_num: Optional[int] = None,
    debug: bool = False,
) -> list[dict]:
    """
    Run conserved island analysis and print results.
    Intended for use from analyze_pdb.py pipeline.

    Returns:
        List of island dicts, or empty list on failure.
    """
    step_label = f"STEP {step_num}: " if step_num else ""
    output_dir = Path(output_dir)

    if verbose:
        print(f"\n{'='*80}")
        print(f"{step_label}Conserved Island Analysis")
        print(f"{'='*80}")
        print(f"System: {output_dir}")
        print(f"Threshold: {min_consistency*100:.0f}%")
        print(f"Min island size: {min_island_size}")
        print(f"{'='*80}\n")

    try:
        islands, direct_pair_counts, total_frames = count_conserved_islands(
            system_dir=output_dir,
            min_consistency=min_consistency,
            min_island_size=min_island_size,
            debug=debug,
        )
    except Exception as e:
        if verbose:
            print(f"  Conserved island analysis skipped: {e}")
        return []

    # Build JSON output for Mol* (id, size, chains, residues with chain/resNum/resName and connectedTo within island)
    # connectedTo = only residues in this island that have a *direct* interaction (edge in final_file; A–B only)
    residue_names = _get_residue_names(output_dir)
    json_islands = []
    for island in islands:
        component = island["component"]
        residues_list = []
        for part in island["Residues"].split(", "):
            part = part.strip()
            if ":" not in part:
                continue
            ch, rnum = part.split(":", 1)
            ch = ch.strip()
            try:
                rnum = int(rnum)
            except ValueError:
                pass
            node = (ch, rnum)
            res_name = residue_names.get(node, "UNK")
            # Only residues in this island that are *direct* interaction partners (edge in final_file; cross-chain only),
            # and only if the direct interaction meets the conservation threshold.
            connected_to = []
            for other in component:
                if other == node:
                    continue
                pair = frozenset({node, other})
                count = direct_pair_counts.get(pair, 0)
                if count / total_frames >= min_consistency:
                    c, n = other
                    connected_to.append({
                        "chain": c,
                        "resNum": n,
                        "resName": residue_names.get((c, n), "UNK"),
                    })
            connected_to.sort(key=lambda x: (x["chain"], x["resNum"]))
            # Include every island residue (for Mol* highlighting). Table can filter to rows with connectedTo.
            residues_list.append({
                "chain": ch,
                "resNum": rnum,
                "resName": res_name,
                "connectedTo": connected_to,
            })

        json_islands.append({
            "id": island["Island_id"],
            "size": len(residues_list),
            "chains": [c.strip() for c in island["Chains"].split(",")],
            "residues": residues_list,
        })

    out_file = output_dir / "_conserved_islands.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"islands": json_islands}, f, indent=2)

    if verbose:
        csv_count = len(_find_final_files(output_dir))
        print(f"  {csv_count} frames analyzed, {len(islands)} conserved island(s) found")
        print(f"  Wrote {out_file}\n")
        for island in islands:
            print(f"  Island {island['Island_id']} (size={island['Island_size']}):")
            print(f"    Chains: {island['Chains']}")
            print(f"    Residues: {island['Residues']}")
            print()

    return islands


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect conserved interaction islands across an MD trajectory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python conserved_islands.py systems/1ULL
  python conserved_islands.py systems/1ULL --threshold 0.80
  python conserved_islands.py systems/1ULL --threshold 0.50 --min-size 3
  python conserved_islands.py systems/1ULL --debug
        """,
    )
    parser.add_argument(
        "system_dir",
        help="Path to a system directory containing frame_N/ sub-folders.",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.70,
        help="Minimum conservation fraction (default: 0.70 = 70%%).",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=3,
        help="Minimum number of residues in an island (default: 3; pairs of 2 are excluded).",
    )
    parser.add_argument("--debug", action="store_true", help="Print per-frame progress.")
    args = parser.parse_args()

    run_conserved_islands(
        output_dir=args.system_dir,
        min_consistency=args.threshold,
        min_island_size=args.min_size,
        verbose=True,
        step_num=None,
        debug=args.debug,
    )
