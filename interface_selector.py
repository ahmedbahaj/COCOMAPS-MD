#!/usr/bin/env python3
"""
Interface Selector with Bridging Waters
Selects interface residues between two protein chains AND water molecules
that bridge both chains (within cutoff distance of heavy atoms from BOTH chains).
"""

import sys
import os
from datetime import datetime
import numpy as np
import MDAnalysis as mda
from MDAnalysis.analysis.distances import distance_array


def select_interface(input_pdb, output_pdb=None, chain_a='A', chain_b='B', 
                     cutoff=5.0, water_cutoff=None, verbose=True):
    """
    Select interface residues and bridging waters from a PDB file.
    
    This is the main entry point for programmatic use (e.g., from analyze_pdb.py).
    
    Parameters:
    -----------
    input_pdb : str
        Path to input PDB file
    output_pdb : str or None
        Path to output PDB file. If None, auto-generates based on input name.
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
    str : Path to the output PDB file
    """
    # Use same cutoff for waters if not specified
    if water_cutoff is None:
        water_cutoff = cutoff
    
    # Auto-generate output name if not provided
    if output_pdb is None:
        base = os.path.splitext(input_pdb)[0]
        output_pdb = f"{base}_interface.pdb"
    
    if verbose:
        print(f"Input PDB: {input_pdb}")
        print(f"Output PDB: {output_pdb}")
        print(f"Chains: {chain_a}, {chain_b}")
        print(f"Interface cutoff: {cutoff} Å")
        print(f"Water cutoff: {water_cutoff} Å")
    
    # Load the structure/trajectory
    universe = mda.Universe(input_pdb)
    
    num_frames = len(universe.trajectory)
    if verbose:
        print(f"Loaded structure with {num_frames} frame(s)")
        print(f"Scanning frames for interface residues...")
    
    # Count total protein atoms in the chains being analyzed
    total_protein_sel = universe.select_atoms(f"(segid {chain_a} or segid {chain_b}) and protein")
    if len(total_protein_sel) == 0:
        try:
            all_protein = universe.select_atoms("protein")
            total_protein_sel = all_protein[(all_protein.segids == chain_a) | (all_protein.segids == chain_b)]
        except:
            total_protein_sel = universe.select_atoms(f"segid {chain_a} or segid {chain_b}")
    
    total_protein_atoms = len(total_protein_sel)
    
    # Find interface residues across all frames
    keep_list, chain_a_atoms_obj, chain_b_atoms_obj = find_global_interface(
        universe, chain_a, chain_b, cutoff
    )
    chain_a_atoms_count = len(chain_a_atoms_obj)
    chain_b_atoms_count = len(chain_b_atoms_obj)
    
    if verbose:
        print(f"Total unique interface residues found: {len(keep_list)}")
    
    # Find bridging waters
    if verbose:
        print(f"Scanning for bridging water molecules...")
    
    bridging_water_resids, total_waters = find_bridging_waters(
        universe, chain_a, chain_b, water_cutoff, verbose
    )
    
    if verbose:
        print(f"Bridging waters found: {len(bridging_water_resids)}/{total_waters}")
    
    # Create selection string for protein residues to keep
    protein_selections = []
    for chain_id, resnum in keep_list:
        protein_selections.append(f"(segid {chain_id} and resid {resnum})")
    
    # Build output atom group
    if not protein_selections and not bridging_water_resids:
        if verbose:
            print("Warning: No interface residues or bridging waters found. Output file will be empty.")
        preserved_protein_atoms = 0
        preserved_water_atoms = 0
        deleted_protein_atoms = total_protein_atoms
        deleted_water_atoms = total_waters * 3  # Approximate (O + 2H per water)
        empty_sel = universe.select_atoms("none")
        output_atoms = empty_sel
    else:
        # Select interface protein atoms
        if protein_selections:
            protein_selection_string = " or ".join(protein_selections)
            interface_protein_atoms = universe.select_atoms(protein_selection_string)
        else:
            interface_protein_atoms = universe.select_atoms("none")
        
        preserved_protein_atoms = len(interface_protein_atoms)
        deleted_protein_atoms = total_protein_atoms - preserved_protein_atoms
        
        # Select bridging water atoms (full residues, not just oxygen)
        if bridging_water_resids:
            water_resid_str = " ".join(map(str, bridging_water_resids))
            water_selection = f"(resname HOH or resname WAT or resname TIP3 or resname SOL) and resid {water_resid_str}"
            bridging_water_atoms = universe.select_atoms(water_selection)
        else:
            bridging_water_atoms = universe.select_atoms("none")
        
        preserved_water_atoms = len(bridging_water_atoms)
        # Total water atoms in input
        all_water_atoms = universe.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL")
        deleted_water_atoms = len(all_water_atoms) - preserved_water_atoms
        
        # Combine protein and water atoms
        if len(interface_protein_atoms) > 0 and len(bridging_water_atoms) > 0:
            output_atoms = interface_protein_atoms + bridging_water_atoms
        elif len(interface_protein_atoms) > 0:
            output_atoms = interface_protein_atoms
        elif len(bridging_water_atoms) > 0:
            output_atoms = bridging_water_atoms
        else:
            output_atoms = universe.select_atoms("none")
    
    # Write the output PDB
    if len(output_atoms) > 0:
        if len(universe.trajectory) > 1:
            with mda.Writer(output_pdb, output_atoms.n_atoms) as writer:
                for ts in universe.trajectory:
                    writer.write(output_atoms)
        else:
            output_atoms.write(output_pdb)
    else:
        universe.select_atoms("none").write(output_pdb)
    
    # Generate and write log file
    log_file = os.path.splitext(output_pdb)[0] + "_summary.txt"
    write_summary_log(
        input_pdb, output_pdb, log_file, chain_a, chain_b, cutoff, water_cutoff,
        num_frames, chain_a_atoms_count, chain_b_atoms_count, keep_list,
        total_protein_atoms, preserved_protein_atoms, deleted_protein_atoms,
        total_waters, len(bridging_water_resids), preserved_water_atoms, deleted_water_atoms
    )
    
    if verbose:
        total_preserved = preserved_protein_atoms + preserved_water_atoms
        total_original = total_protein_atoms + len(universe.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL"))
        print(f"\nProtein atoms: {preserved_protein_atoms}/{total_protein_atoms} preserved")
        print(f"Water molecules: {len(bridging_water_resids)}/{total_waters} preserved (bridging)")
        print(f"Total atoms preserved: {total_preserved}")
        if total_original > 0:
            print(f"Overall preservation rate: {(total_preserved / total_original) * 100:.1f}%")
        print(f"Output saved to: {output_pdb}")
        print(f"Summary log: {log_file}")
    
    return output_pdb


def find_global_interface(universe, chain_a, chain_b, cutoff=5.0):
    """
    Scans all frames (models) to find residues that are EVER within 
    the cutoff distance of the partner chain.
    
    Parameters:
    -----------
    universe : MDAnalysis.Universe
        The loaded trajectory/structure
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    cutoff : float
        Distance cutoff in Angstroms (default: 5.0)
    
    Returns:
    --------
    tuple : (set of (chain_id, residue_id) tuples to keep, chain_a_atoms, chain_b_atoms)
    """
    global_keep_list = set()
    
    # Select protein atoms from both chains
    chain_a_atoms = universe.select_atoms(f"segid {chain_a} and protein")
    chain_b_atoms = universe.select_atoms(f"segid {chain_b} and protein")
    
    # If that doesn't work, try alternative methods
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
    
    print(f"Chain {chain_a}: {len(chain_a_atoms)} atoms")
    print(f"Chain {chain_b}: {len(chain_b_atoms)} atoms")
    
    # Iterate through all frames
    for ts in universe.trajectory:
        distances = distance_array(
            chain_a_atoms.positions, 
            chain_b_atoms.positions, 
            box=universe.dimensions if hasattr(universe, 'dimensions') and universe.dimensions is not None else None
        )
        
        # Find minimum distance for each chain A atom to any chain B atom
        min_distances_a = np.min(distances, axis=1)
        close_atoms_a = chain_a_atoms[min_distances_a <= cutoff]
        
        # Find minimum distance for each chain B atom to any chain A atom
        min_distances_b = np.min(distances, axis=0)
        close_atoms_b = chain_b_atoms[min_distances_b <= cutoff]
        
        # Add residues to keep list
        for atom in close_atoms_a:
            res = atom.residue
            global_keep_list.add((chain_a, res.resnum))
        
        for atom in close_atoms_b:
            res = atom.residue
            global_keep_list.add((chain_b, res.resnum))
    
    return global_keep_list, chain_a_atoms, chain_b_atoms


def find_bridging_waters(universe, chain_a, chain_b, cutoff=5.0, verbose=True):
    """
    Find water molecules that bridge both chains (within cutoff of BOTH chains).
    Uses spatial grid hashing for efficient O(N+M) lookup.
    
    A bridging water is defined as a water molecule whose oxygen atom is within
    the cutoff distance of at least one heavy atom from chain A AND at least
    one heavy atom from chain B.
    
    Parameters:
    -----------
    universe : MDAnalysis.Universe
        The loaded trajectory/structure
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    cutoff : float
        Distance cutoff in Angstroms (default: 5.0)
    verbose : bool
        Whether to print progress messages
    
    Returns:
    --------
    tuple : (set of water residue IDs to keep, total water count)
    """
    # Select heavy atoms (not hydrogen) from each chain
    # Heavy atoms = all atoms except hydrogen
    chain_a_heavy = universe.select_atoms(f"segid {chain_a} and protein and not name H*")
    chain_b_heavy = universe.select_atoms(f"segid {chain_b} and protein and not name H*")
    
    # Fallback if segid doesn't work
    if len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        chain_a_heavy = universe.select_atoms(f"segid {chain_a} and not name H*")
        chain_b_heavy = universe.select_atoms(f"segid {chain_b} and not name H*")
    
    # Select water oxygen atoms
    try:
        water_oxygens = universe.select_atoms(
            "(resname HOH and name O) or "
            "(resname WAT and name O) or "
            "(resname TIP3 and name OH2) or "
            "(resname SOL and name OW)"
        )
    except:
        water_oxygens = universe.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL")
    
    total_waters = len(water_oxygens)
    
    if verbose:
        print(f"Chain {chain_a} heavy atoms: {len(chain_a_heavy)}")
        print(f"Chain {chain_b} heavy atoms: {len(chain_b_heavy)}")
        print(f"Total water molecules: {total_waters}")
    
    if total_waters == 0:
        return set(), 0
    
    if len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        if verbose:
            print("Warning: One or both chains have no heavy atoms. No bridging waters found.")
        return set(), total_waters
    
    # Use spatial grid hashing for efficient lookup
    # We need waters that are near BOTH chain A AND chain B
    grid_size = cutoff
    
    bridging_resids = set()
    
    # Iterate through all frames to find waters that EVER bridge both chains
    for ts in universe.trajectory:
        # Build grid for chain A heavy atoms
        grid_a = set()
        for pos in chain_a_heavy.positions:
            cell_x = int(np.floor(pos[0] / grid_size))
            cell_y = int(np.floor(pos[1] / grid_size))
            cell_z = int(np.floor(pos[2] / grid_size))
            # Mark cell and all 26 neighbors
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        grid_a.add((cell_x + dx, cell_y + dy, cell_z + dz))
        
        # Build grid for chain B heavy atoms
        grid_b = set()
        for pos in chain_b_heavy.positions:
            cell_x = int(np.floor(pos[0] / grid_size))
            cell_y = int(np.floor(pos[1] / grid_size))
            cell_z = int(np.floor(pos[2] / grid_size))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        grid_b.add((cell_x + dx, cell_y + dy, cell_z + dz))
        
        # Check each water oxygen - must be in BOTH grids
        for water_atom in water_oxygens:
            pos = water_atom.position
            w_cell = (
                int(np.floor(pos[0] / grid_size)),
                int(np.floor(pos[1] / grid_size)),
                int(np.floor(pos[2] / grid_size))
            )
            
            # Water must be near BOTH chain A AND chain B
            if w_cell in grid_a and w_cell in grid_b:
                bridging_resids.add(water_atom.resid)
    
    return bridging_resids, total_waters


def write_summary_log(input_pdb, output_pdb, log_file, chain_a, chain_b, 
                      cutoff, water_cutoff, num_frames, 
                      chain_a_atoms, chain_b_atoms, keep_list,
                      total_protein_atoms, preserved_protein_atoms, deleted_protein_atoms,
                      total_waters, bridging_waters, preserved_water_atoms, deleted_water_atoms):
    """
    Write a comprehensive summary log to a text file.
    """
    with open(log_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("INTERFACE SELECTION SUMMARY (WITH BRIDGING WATERS)\n")
        f.write("=" * 80 + "\n\n")
        
        # Timestamp
        f.write(f"Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # File information
        f.write("FILE INFORMATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Input PDB file:  {input_pdb}\n")
        f.write(f"Output PDB file: {output_pdb}\n")
        f.write(f"Log file:        {log_file}\n\n")
        
        # Parameters
        f.write("PARAMETERS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Chain A:              {chain_a}\n")
        f.write(f"Chain B:              {chain_b}\n")
        f.write(f"Interface cutoff:     {cutoff} Å\n")
        f.write(f"Water bridge cutoff:  {water_cutoff} Å\n")
        f.write(f"Number of frames:     {num_frames}\n\n")
        
        # Chain statistics
        f.write("CHAIN STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Chain {chain_a} atoms: {chain_a_atoms}\n")
        f.write(f"Chain {chain_b} atoms: {chain_b_atoms}\n")
        f.write(f"Total protein atoms in chains {chain_a} and {chain_b}: {total_protein_atoms}\n\n")
        
        # Interface residues
        f.write("INTERFACE RESIDUES\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total unique interface residues found: {len(keep_list)}\n\n")
        
        # Sort residues by chain and residue number
        sorted_residues = sorted(keep_list, key=lambda x: (x[0], x[1]))
        
        chain_a_residues = [res for res in sorted_residues if res[0] == chain_a]
        chain_b_residues = [res for res in sorted_residues if res[0] == chain_b]
        
        f.write(f"Chain {chain_a} interface residues ({len(chain_a_residues)}):\n")
        if chain_a_residues:
            res_nums = [str(res[1]) for res in chain_a_residues]
            for i in range(0, len(res_nums), 20):
                f.write(f"  {', '.join(res_nums[i:i+20])}\n")
        else:
            f.write("  None\n")
        f.write("\n")
        
        f.write(f"Chain {chain_b} interface residues ({len(chain_b_residues)}):\n")
        if chain_b_residues:
            res_nums = [str(res[1]) for res in chain_b_residues]
            for i in range(0, len(res_nums), 20):
                f.write(f"  {', '.join(res_nums[i:i+20])}\n")
        else:
            f.write("  None\n")
        f.write("\n")
        
        # Bridging waters section
        f.write("BRIDGING WATERS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total water molecules in input:  {total_waters}\n")
        f.write(f"Bridging waters (near both chains): {bridging_waters}\n")
        f.write(f"Waters discarded: {total_waters - bridging_waters}\n")
        if total_waters > 0:
            f.write(f"Bridging water percentage: {(bridging_waters / total_waters) * 100:.2f}%\n")
        f.write("\n")
        
        # Atom statistics
        f.write("ATOM STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Protein atoms preserved: {preserved_protein_atoms}/{total_protein_atoms}\n")
        f.write(f"Water atoms preserved:   {preserved_water_atoms}\n")
        f.write(f"Total atoms preserved:   {preserved_protein_atoms + preserved_water_atoms}\n")
        if total_protein_atoms > 0:
            f.write(f"Protein preservation rate: {(preserved_protein_atoms / total_protein_atoms) * 100:.2f}%\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF SUMMARY\n")
        f.write("=" * 80 + "\n")


def main(input_pdb, output_pdb, chain_a, chain_b, cutoff=5.0, water_cutoff=None):
    """
    Main function to extract interface residues and bridging waters from a PDB file.
    
    Parameters:
    -----------
    input_pdb : str
        Path to input PDB file
    output_pdb : str
        Path to output PDB file
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    cutoff : float
        Distance cutoff in Angstroms (default: 5.0)
    water_cutoff : float
        Water bridge cutoff in Angstroms (default: same as cutoff)
    """
    select_interface(
        input_pdb, 
        output_pdb, 
        chain_a, 
        chain_b, 
        cutoff=cutoff, 
        water_cutoff=water_cutoff,
        verbose=True
    )


if __name__ == "__main__":
    # Usage: python interface_selector.py input.pdb output.pdb A B [cutoff] [water_cutoff]
    if len(sys.argv) < 5:
        print("Usage: python interface_selector.py <input.pdb> <output.pdb> <chain1> <chain2> [cutoff] [water_cutoff]")
        print("  cutoff: distance cutoff in Angstroms (default: 5.0)")
        print("  water_cutoff: water bridge cutoff in Angstroms (default: same as cutoff)")
        print()
        print("Bridging waters: Water molecules within cutoff of heavy atoms from BOTH chains")
    else:
        cutoff = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0
        water_cutoff = float(sys.argv[6]) if len(sys.argv) > 6 else None
        main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], cutoff, water_cutoff)
