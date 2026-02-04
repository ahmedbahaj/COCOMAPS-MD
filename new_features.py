# new_features.py
import argparse
from pathlib import Path

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt


def _detect_residue_columns(data: pd.DataFrame):
    """Detect residue number and chain column names. Returns (col_num1, col_num2, col_chain1, col_chain2) or None."""
    cols = {c.strip(): c for c in data.columns}
    # Res. Number 1 / Res. Number 2 (with optional Res. Chain 1 / Res. Chain 2 or Chain 1 / Chain 2)
    if "Res. Number 1" in cols and "Res. Number 2" in cols:
        c1 = cols.get("Res. Chain 1") or cols.get("Chain 1")
        c2 = cols.get("Res. Chain 2") or cols.get("Chain 2")
        return ("Res. Number 1", "Res. Number 2", c1, c2)
    # NA/Protein + Ligand (e.g. NA/Protein Res Number, Ligand Res Number)
    if "NA/Protein Res Number" in cols and "Ligand Res Number" in cols:
        ch1 = cols.get("NA/Protein Chain") or cols.get("RNA chain")
        ch2 = cols.get("Ligand Chain")
        return ("NA/Protein Res Number", "Ligand Res Number", ch1, ch2)
    # RNA + Ligand
    if "RNA Res. Number" in cols and "Ligand Res. Number" in cols:
        ch1 = cols.get("RNA chain") or cols.get("RNA Chain")
        ch2 = cols.get("Ligand Chain")
        return ("RNA Res. Number", "Ligand Res. Number", ch1, ch2)
    return None


def count_island_sizes(data, maxGroupSize=13, debug=False, log_file="island_debug.log", return_graph=False):
    """
    Build a graph from residue–residue interactions and return one row per island (connected component)
    with Island_id, Island_size, Residues (chain:res_num, ...), and Chains (comma-separated).
    Supports column names: Res. Number 1/2, NA/Protein Res Number & Ligand Res Number, or RNA Res. Number & Ligand Res. Number,
    with matching chain columns.
    
    If return_graph=True, returns (islands_df, G) instead of just islands_df.
    """
    def log(msg):
        if debug:
            with open(log_file, "a") as f:
                f.write(str(msg) + "\n")

    if debug:
        open(log_file, "w").close()

    if data is None or data.empty:
        empty_df = pd.DataFrame(columns=["Island_id", "Island_size", "Residues", "Chains"])
        return (empty_df, nx.Graph()) if return_graph else empty_df

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
    
    if return_graph:
        return islands_df, G
    return islands_df


def save_graph_image(G, output_path, title="Residue Interaction Network"):
    """
    Save a visualization of the interaction graph to an image file.
    
    Args:
        G: NetworkX graph with nodes as (chain, residue_number) tuples.
        output_path: Path to save the image (e.g., 'graph.png').
        title: Title for the graph.
    """
    if G.number_of_nodes() == 0:
        print("Warning: Graph is empty, no image saved.")
        return
    
    # Get unique chains for coloring
    chains = sorted(set(chain for chain, _ in G.nodes()))
    color_map = plt.cm.get_cmap('tab10', len(chains))
    chain_colors = {chain: color_map(i) for i, chain in enumerate(chains)}
    
    # Assign colors to nodes based on chain
    node_colors = [chain_colors[chain] for chain, _ in G.nodes()]
    
    # Create labels as "chain:res"
    labels = {node: f"{node[0]}:{node[1]}" for node in G.nodes()}
    
    # Create figure
    plt.figure(figsize=(14, 10))
    
    # Use spring layout for positioning
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500, alpha=0.9)
    nx.draw_networkx_edges(G, pos, alpha=0.5, width=1.5)
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
    
    # Add legend for chains
    legend_handles = [plt.Line2D([0], [0], marker='o', color='w', 
                                  markerfacecolor=chain_colors[chain], 
                                  markersize=10, label=f'Chain {chain}')
                      for chain in chains]
    plt.legend(handles=legend_handles, loc='upper left', fontsize=10)
    
    plt.title(f"{title}\n({G.number_of_nodes()} residues, {G.number_of_edges()} interactions)", fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved graph image to: {output_path}")


def process_final_files(
    path_list,
    output_csv_path=None,
    output_image_path=None,
    debug=False,
    log_file="island_debug.log",
) -> pd.DataFrame:
    """
    Process one or more final-file CSVs and produce a single CSV with island info.

    Each entry in path_list is the path to a *_final_file.csv. The output has one row
    per island per file, with columns: Input_file, Island_id, Island_size, Residues, Chains.
    Rows are ordered by input list order, then by Island_id within each file.

    Args:
        path_list: List of paths (at least one) to final-file CSVs.
        output_csv_path: If set, write the combined result to this CSV file.
        output_image_path: If set, save a graph image to this path.
        debug: Passed to count_island_sizes.
        log_file: Passed to count_island_sizes.

    Returns:
        DataFrame with columns Input_file, Island_id, Island_size, Residues, Chains.
    """
    if not path_list:
        raise ValueError("path_list must contain at least one path")

    all_rows = []
    combined_graph = nx.Graph()  # Combined graph for visualization
    
    for path in path_list:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Final file not found: {path}")
        df = pd.read_csv(p, low_memory=False)
        islands_df, G = count_island_sizes(df, debug=debug, log_file=log_file, return_graph=True)
        
        # Merge graph into combined graph
        combined_graph = nx.compose(combined_graph, G)
        
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
    
    # Save graph image if requested
    if output_image_path is not None:
        save_graph_image(combined_graph, output_image_path)
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run island analysis on one or more final-file CSVs and write a combined CSV."
    )
    parser.add_argument(
        "final_files",
        nargs="+",
        help="Paths to final-file CSVs (at least one).",
    )
    parser.add_argument(
        "-o", "--output",
        default="islands_output.csv",
        help="Output CSV path (default: islands_output.csv).",
    )
    parser.add_argument(
        "-g", "--graph",
        default=None,
        help="Output graph image path (e.g., graph.png). If not set, no image is saved.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    process_final_files(
        path_list=args.final_files,
        output_csv_path=args.output,
        output_image_path=args.graph,
        debug=args.debug,
    )
    print(f"Wrote {args.output} ({len(args.final_files)} input file(s)).")
    if args.graph:
        print(f"Graph image saved to: {args.graph}")