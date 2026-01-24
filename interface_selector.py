#!/usr/bin/env python3
"""
Interface Selector with Bridging Waters (Per-Frame Mode)

Selects interface residues between two protein chains AND water molecules
that bridge both chains (within cutoff distance of heavy atoms from BOTH chains).

Each frame is processed independently - only residues at the interface IN THAT FRAME
are written to that frame's output PDB. This means atom counts may vary between frames.
"""

import sys
import os
from datetime import datetime
import time
import numpy as np
import MDAnalysis as mda
from MDAnalysis.analysis.distances import distance_array


def select_interface_per_frame(input_pdb, output_dir, chain_a='A', chain_b='B',
                                cutoff=5.0, water_cutoff=5.0, verbose=True):
    """
    Select interface residues and bridging waters on a PER-FRAME basis.
    
    Each frame gets its own keep_list - only residues at the interface IN THAT FRAME
    are written to that frame's output PDB. This means atom counts may vary between frames.
    
    This function combines interface selection with frame splitting for efficiency.
    
    Parameters:
    -----------
    input_pdb : str
        Path to input PDB file (can be multi-model/trajectory)
    output_dir : str
        Output directory. Creates frame_N/frame_N.pdb for each frame.
    chain_a : str
        Chain identifier for the first chain (default: 'A')
    chain_b : str
        Chain identifier for the second chain (default: 'B')
    cutoff : float
        Distance cutoff for interface residues in Angstroms (default: 5.0)
    water_cutoff : float or None
        Distance cutoff for bridging waters in Angstroms. If None, uses same as cutoff.
    verbose : bool
        Whether to print progress messages (default: True)
    
    Returns:
    --------
    tuple : (output_dir, frame_count)
    """
    start_time = time.time()
    
    # Use same cutoff for waters if not specified
    if water_cutoff is None:
        water_cutoff = cutoff
    
    if verbose:
        print(f"Input PDB: {input_pdb}")
        print(f"Output Directory: {output_dir}")
        print(f"Chains: {chain_a}, {chain_b}")
        print(f"Interface cutoff: {cutoff} Å")
        print(f"Water cutoff: {water_cutoff} Å")
        print(f"Mode: Per-frame interface selection")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the structure/trajectory
    universe = mda.Universe(input_pdb)
    num_frames = len(universe.trajectory)
    
    if verbose:
        print(f"Loaded structure with {num_frames} frame(s)")
    
    # Pre-select atom groups (reused across frames - positions auto-update)
    chain_a_atoms = universe.select_atoms(f"segid {chain_a} and protein")
    chain_b_atoms = universe.select_atoms(f"segid {chain_b} and protein")
    
    # Fallback if segid doesn't work
    if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
        chain_a_atoms = universe.select_atoms(f"segid {chain_a}")
        chain_b_atoms = universe.select_atoms(f"segid {chain_b}")
        
        if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
            all_protein = universe.select_atoms("protein")
            try:
                chain_a_atoms = all_protein[all_protein.segids == chain_a]
                chain_b_atoms = all_protein[all_protein.segids == chain_b]
            except:
                chain_a_atoms = universe.select_atoms(f"segid {chain_a}")
                chain_b_atoms = universe.select_atoms(f"segid {chain_b}")
    
    # Heavy atoms for water bridging
    chain_a_heavy = universe.select_atoms(f"segid {chain_a} and protein and not name H*")
    chain_b_heavy = universe.select_atoms(f"segid {chain_b} and protein and not name H*")
    
    if len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        chain_a_heavy = universe.select_atoms(f"segid {chain_a} and not name H*")
        chain_b_heavy = universe.select_atoms(f"segid {chain_b} and not name H*")
    
    # Water oxygens
    try:
        water_oxygens = universe.select_atoms(
            "(resname HOH and name O) or "
            "(resname WAT and name O) or "
            "(resname TIP3 and name OH2) or "
            "(resname SOL and name OW)"
        )
    except:
        water_oxygens = universe.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL")
    
    if verbose:
        print(f"Chain {chain_a}: {len(chain_a_atoms)} protein atoms, {len(chain_a_heavy)} heavy atoms")
        print(f"Chain {chain_b}: {len(chain_b_atoms)} protein atoms, {len(chain_b_heavy)} heavy atoms")
        print(f"Total water molecules: {len(water_oxygens)}")
        print(f"\nProcessing frames...")
    
    # Statistics tracking
    total_protein_atoms_original = len(chain_a_atoms) + len(chain_b_atoms)
    total_water_original = len(water_oxygens)
    frame_stats = []
    
    # Process each frame
    for frame_idx, ts in enumerate(universe.trajectory):
        frame_num = frame_idx + 1
        
        # Find interface residues for THIS frame
        keep_list = _find_interface_single_frame(
            chain_a_atoms, chain_b_atoms, chain_a, chain_b, cutoff
        )
        
        # Find bridging waters for THIS frame
        bridging_water_resids = _find_bridging_waters_single_frame(
            chain_a_heavy, chain_b_heavy, water_oxygens, water_cutoff
        )
        
        # Build selection for interface protein atoms
        if keep_list:
            protein_selections = [f"(segid {c} and resid {r})" for c, r in keep_list]
            protein_selection_string = " or ".join(protein_selections)
            interface_protein_atoms = universe.select_atoms(protein_selection_string)
        else:
            interface_protein_atoms = universe.select_atoms("none")
        
        # Build selection for bridging water atoms
        if bridging_water_resids:
            water_resid_str = " ".join(map(str, bridging_water_resids))
            water_selection = f"(resname HOH or resname WAT or resname TIP3 or resname SOL) and resid {water_resid_str}"
            bridging_water_atoms = universe.select_atoms(water_selection)
        else:
            bridging_water_atoms = universe.select_atoms("none")
        
        # Combine protein and water atoms
        if len(interface_protein_atoms) > 0 and len(bridging_water_atoms) > 0:
            output_atoms = interface_protein_atoms + bridging_water_atoms
        elif len(interface_protein_atoms) > 0:
            output_atoms = interface_protein_atoms
        elif len(bridging_water_atoms) > 0:
            output_atoms = bridging_water_atoms
        else:
            output_atoms = universe.select_atoms("none")
        
        # Create frame directory and write PDB
        frame_folder = os.path.join(output_dir, f"frame_{frame_num}")
        os.makedirs(frame_folder, exist_ok=True)
        frame_file = os.path.join(frame_folder, f"frame_{frame_num}.pdb")
        
        if len(output_atoms) > 0:
            output_atoms.write(frame_file)
        else:
            universe.select_atoms("none").write(frame_file)
        
        # Track statistics
        frame_stats.append({
            'frame': frame_num,
            'interface_residues': len(keep_list),
            'protein_atoms': len(interface_protein_atoms),
            'bridging_waters': len(bridging_water_resids),
            'water_atoms': len(bridging_water_atoms),
            'total_atoms': len(output_atoms)
        })
        
        if verbose:
            print(f"  Frame {frame_num}: {len(keep_list)} residues, "
                  f"{len(interface_protein_atoms)} protein atoms, "
                  f"{len(bridging_water_resids)} waters → {len(output_atoms)} total atoms")
    
    elapsed = time.time() - start_time
    
    # Write summary log
    log_file = os.path.join(output_dir, "interface_selection_summary.txt")
    _write_per_frame_summary_log(
        input_pdb, output_dir, log_file, chain_a, chain_b, cutoff, water_cutoff,
        num_frames, len(chain_a_atoms), len(chain_b_atoms),
        total_protein_atoms_original, total_water_original, frame_stats
    )
    
    if verbose:
        # Calculate averages
        avg_residues = sum(s['interface_residues'] for s in frame_stats) / num_frames
        avg_protein = sum(s['protein_atoms'] for s in frame_stats) / num_frames
        avg_waters = sum(s['bridging_waters'] for s in frame_stats) / num_frames
        avg_total = sum(s['total_atoms'] for s in frame_stats) / num_frames
        
        print(f"\n{'='*60}")
        print(f"Per-Frame Interface Selection Complete")
        print(f"{'='*60}")
        print(f"Frames processed: {num_frames}")
        print(f"Time elapsed: {elapsed:.2f} seconds")
        print(f"\nAverages per frame:")
        print(f"  Interface residues: {avg_residues:.1f}")
        print(f"  Protein atoms: {avg_protein:.1f}")
        print(f"  Bridging waters: {avg_waters:.1f}")
        print(f"  Total atoms: {avg_total:.1f}")
        print(f"\nOutput directory: {output_dir}")
        print(f"Summary log: {log_file}")
    
    return output_dir, num_frames


def _find_interface_single_frame(chain_a_atoms, chain_b_atoms, chain_a, chain_b, cutoff):
    """
    Find interface residues for the CURRENT frame only.
    Atom positions are already set to current frame by MDAnalysis trajectory iteration.
    
    Returns:
    --------
    set : Set of (chain_id, residue_number) tuples at interface in this frame
    """
    keep_list = set()
    
    if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
        return keep_list
    
    # Calculate all pairwise distances
    distances = distance_array(
        chain_a_atoms.positions,
        chain_b_atoms.positions,
        box=None  # Assuming no periodic boundary conditions for protein structures
    )
    
    # Find chain A atoms close to any chain B atom
    min_distances_a = np.min(distances, axis=1)
    close_mask_a = min_distances_a <= cutoff
    
    # Find chain B atoms close to any chain A atom
    min_distances_b = np.min(distances, axis=0)
    close_mask_b = min_distances_b <= cutoff
    
    # Get residue info for close atoms in chain A
    for atom in chain_a_atoms[close_mask_a]:
        keep_list.add((chain_a, atom.residue.resnum))
    
    # Get residue info for close atoms in chain B
    for atom in chain_b_atoms[close_mask_b]:
        keep_list.add((chain_b, atom.residue.resnum))
    
    return keep_list


def _find_bridging_waters_single_frame(chain_a_heavy, chain_b_heavy, water_oxygens, cutoff):
    """
    Find bridging water molecules for the CURRENT frame only.
    Uses distance_array for accurate distance calculations.
    
    A bridging water must be within cutoff of BOTH chain A AND chain B heavy atoms.
    
    Returns:
    --------
    set : Set of water residue IDs that bridge both chains in this frame
    """
    if len(water_oxygens) == 0 or len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        return set()
    
    bridging_resids = set()
    cutoff_sq = cutoff * cutoff  # Use squared distance for efficiency
    
    # Get positions as numpy arrays
    water_positions = water_oxygens.positions
    chain_a_positions = chain_a_heavy.positions
    chain_b_positions = chain_b_heavy.positions
    
    # Calculate distances from each water to all chain A heavy atoms
    # Returns shape (n_waters, n_chain_a_atoms)
    dist_to_a = distance_array(water_positions, chain_a_positions, box=None)
    
    # Calculate distances from each water to all chain B heavy atoms
    # Returns shape (n_waters, n_chain_b_atoms)
    dist_to_b = distance_array(water_positions, chain_b_positions, box=None)
    
    # For each water, find minimum distance to each chain
    min_dist_to_a = np.min(dist_to_a, axis=1)  # Shape: (n_waters,)
    min_dist_to_b = np.min(dist_to_b, axis=1)  # Shape: (n_waters,)
    
    # Water must be within cutoff of BOTH chains
    bridging_mask = (min_dist_to_a <= cutoff) & (min_dist_to_b <= cutoff)
    
    # Get residue IDs of bridging waters
    for i, water_atom in enumerate(water_oxygens):
        if bridging_mask[i]:
            bridging_resids.add(water_atom.resid)
    
    return bridging_resids


def _write_per_frame_summary_log(input_pdb, output_dir, log_file, chain_a, chain_b,
                                  cutoff, water_cutoff, num_frames,
                                  chain_a_atoms, chain_b_atoms,
                                  total_protein_atoms, total_waters, frame_stats):
    """
    Write a summary log for per-frame interface selection.
    """
    with open(log_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PER-FRAME INTERFACE SELECTION SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("FILE INFORMATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Input PDB file:    {input_pdb}\n")
        f.write(f"Output directory:  {output_dir}\n")
        f.write(f"Log file:          {log_file}\n\n")
        
        f.write("PARAMETERS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Chain A:              {chain_a}\n")
        f.write(f"Chain B:              {chain_b}\n")
        f.write(f"Interface cutoff:     {cutoff} Å\n")
        f.write(f"Water bridge cutoff:  {water_cutoff} Å\n")
        f.write(f"Number of frames:     {num_frames}\n")
        f.write(f"Selection mode:       Per-frame (dynamic)\n\n")
        
        f.write("CHAIN STATISTICS (Original)\n")
        f.write("-" * 80 + "\n")
        f.write(f"Chain {chain_a} atoms: {chain_a_atoms}\n")
        f.write(f"Chain {chain_b} atoms: {chain_b_atoms}\n")
        f.write(f"Total protein atoms:  {total_protein_atoms}\n")
        f.write(f"Total water molecules: {total_waters}\n\n")
        
        f.write("PER-FRAME STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Frame':<8} {'Residues':<10} {'Protein':<10} {'Waters':<10} {'Total':<10}\n")
        f.write("-" * 80 + "\n")
        
        for s in frame_stats:
            f.write(f"{s['frame']:<8} {s['interface_residues']:<10} "
                    f"{s['protein_atoms']:<10} {s['bridging_waters']:<10} "
                    f"{s['total_atoms']:<10}\n")
        
        f.write("-" * 80 + "\n")
        
        # Averages
        avg_residues = sum(s['interface_residues'] for s in frame_stats) / num_frames
        avg_protein = sum(s['protein_atoms'] for s in frame_stats) / num_frames
        avg_waters = sum(s['bridging_waters'] for s in frame_stats) / num_frames
        avg_total = sum(s['total_atoms'] for s in frame_stats) / num_frames
        
        f.write(f"{'Average':<8} {avg_residues:<10.1f} {avg_protein:<10.1f} "
                f"{avg_waters:<10.1f} {avg_total:<10.1f}\n\n")
        
        # Min/Max
        min_atoms = min(s['total_atoms'] for s in frame_stats)
        max_atoms = max(s['total_atoms'] for s in frame_stats)
        f.write(f"Minimum atoms in a frame: {min_atoms}\n")
        f.write(f"Maximum atoms in a frame: {max_atoms}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF SUMMARY\n")
        f.write("=" * 80 + "\n")


if __name__ == "__main__":
    # Command-line interface for per-frame interface selection
    if len(sys.argv) < 3:
        print("Usage: python interface_selector.py <input.pdb> <output_dir> [chain_a] [chain_b] [cutoff] [water_cutoff]")
        print()
        print("Arguments:")
        print("  input.pdb     Input PDB file (can be multi-model)")
        print("  output_dir    Output directory for frame folders")
        print("  chain_a       First chain ID (default: A)")
        print("  chain_b       Second chain ID (default: B)")
        print("  cutoff        Interface cutoff in Angstroms (default: 5.0)")
        print("  water_cutoff  Water bridge cutoff in Angstroms (default: same as cutoff)")
        print()
        print("Output:")
        print("  Creates output_dir/frame_N/frame_N.pdb for each frame")
        print("  Each frame contains only atoms at the interface IN THAT FRAME")
        print()
        print("Bridging waters: Water molecules within cutoff of heavy atoms from BOTH chains")
        sys.exit(1)
    
    input_pdb = sys.argv[1]
    output_dir = sys.argv[2]
    chain_a = sys.argv[3] if len(sys.argv) > 3 else 'A'
    chain_b = sys.argv[4] if len(sys.argv) > 4 else 'B'
    cutoff = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0
    water_cutoff = float(sys.argv[6]) if len(sys.argv) > 6 else None
    
    select_interface_per_frame(
        input_pdb, 
        output_dir, 
        chain_a, 
        chain_b, 
        cutoff=cutoff, 
        water_cutoff=water_cutoff,
        verbose=True
    )
