import sys
import os
from datetime import datetime
import numpy as np
import MDAnalysis as mda
from MDAnalysis.analysis.distances import distance_array


def select_interface(input_pdb, output_pdb=None, chain_a='A', chain_b='B', cutoff=5.0, verbose=True):
    """
    Select interface residues from a PDB file and write to a new file.
    
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
        Distance cutoff in Angstroms (default: 7.0)
    verbose : bool
        Whether to print progress messages (default: True)
    
    Returns:
    --------
    str : Path to the output PDB file
    """
    # Auto-generate output name if not provided
    if output_pdb is None:
        base = os.path.splitext(input_pdb)[0]
        output_pdb = f"{base}_interface.pdb"
    
    if verbose:
        print(f"Input PDB: {input_pdb}")
        print(f"Output PDB: {output_pdb}")
        print(f"Chains: {chain_a}, {chain_b}")
        print(f"Cutoff: {cutoff} Å")
    
    # Load the structure/trajectory
    universe = mda.Universe(input_pdb)
    
    num_frames = len(universe.trajectory)
    if verbose:
        print(f"Loaded structure with {num_frames} frame(s)")
        print(f"Scanning frames for interface residues...")
    
    # Count total atoms in the chains being analyzed
    total_atoms_sel = universe.select_atoms(f"segid {chain_a} or segid {chain_b}")
    if len(total_atoms_sel) == 0:
        try:
            all_protein = universe.select_atoms("protein")
            total_atoms_sel = all_protein[(all_protein.segids == chain_a) | (all_protein.segids == chain_b)]
        except:
            total_atoms_sel = universe.select_atoms(f"segid {chain_a} or segid {chain_b}")
    
    total_atoms = len(total_atoms_sel)
    
    # Find interface residues across all frames
    keep_list, chain_a_atoms_obj, chain_b_atoms_obj = find_global_interface(universe, chain_a, chain_b, cutoff)
    chain_a_atoms_count = len(chain_a_atoms_obj)
    chain_b_atoms_count = len(chain_b_atoms_obj)
    
    if verbose:
        print(f"Total unique interface residues found: {len(keep_list)}")
    
    # Create selection string for residues to keep
    selections = []
    for chain_id, resnum in keep_list:
        selections.append(f"(segid {chain_id} and resid {resnum})")
    
    if not selections:
        if verbose:
            print("Warning: No interface residues found. Output file will be empty.")
        preserved_atoms = 0
        deleted_atoms = total_atoms
        empty_sel = universe.select_atoms("none")
        empty_sel.write(output_pdb)
    else:
        selection_string = " or ".join(selections)
        interface_atoms = universe.select_atoms(selection_string)
        preserved_atoms = len(interface_atoms)
        deleted_atoms = total_atoms - preserved_atoms
        
        # Write the selected atoms to output PDB
        if len(universe.trajectory) > 1:
            with mda.Writer(output_pdb, interface_atoms.n_atoms) as writer:
                for ts in universe.trajectory:
                    writer.write(interface_atoms)
        else:
            interface_atoms.write(output_pdb)
    
    # Generate and write log file
    log_file = os.path.splitext(output_pdb)[0] + "_summary.txt"
    write_summary_log(input_pdb, output_pdb, log_file, chain_a, chain_b, cutoff,
                     num_frames, chain_a_atoms_count, chain_b_atoms_count, keep_list,
                     total_atoms, preserved_atoms, deleted_atoms)
    
    if verbose:
        print(f"Preserved atoms: {preserved_atoms}/{total_atoms}")
        if total_atoms > 0:
            print(f"Preservation rate: {(preserved_atoms / total_atoms) * 100:.1f}%")
        print(f"Output saved to: {output_pdb}")
        print(f"Summary log: {log_file}")
    
    return output_pdb


def find_global_interface(universe, chain_a, chain_b, cutoff=6.0):
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
        Distance cutoff in Angstroms (default: 6.0)
    
    Returns:
    --------
    tuple : (set of (chain_id, residue_id) tuples to keep, chain_a_atoms, chain_b_atoms)
    """
    global_keep_list = set()
    
    # Select atoms from both chains
    # In MDAnalysis, PDB chains are typically accessed via segid
    # Try segid first (most common for PDB files)
    chain_a_atoms = universe.select_atoms(f"segid {chain_a} and protein")
    chain_b_atoms = universe.select_atoms(f"segid {chain_b} and protein")
    
    # If that doesn't work, try alternative methods
    if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
        # Try without protein filter first
        chain_a_atoms = universe.select_atoms(f"segid {chain_a}")
        chain_b_atoms = universe.select_atoms(f"segid {chain_b}")
        
        # If still empty, chains might be stored differently
        if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
            # Fallback: use chain attribute if available
            all_protein = universe.select_atoms("protein")
            try:
                chain_a_atoms = all_protein[all_protein.segids == chain_a]
                chain_b_atoms = all_protein[all_protein.segids == chain_b]
            except:
                # Last resort: assume chains are in segids
                chain_a_atoms = universe.select_atoms(f"segid {chain_a}")
                chain_b_atoms = universe.select_atoms(f"segid {chain_b}")
    
    print(f"Chain {chain_a}: {len(chain_a_atoms)} atoms")
    print(f"Chain {chain_b}: {len(chain_b_atoms)} atoms")
    
    # Iterate through all frames
    for ts in universe.trajectory:
        # Calculate distance matrix between chain A and chain B atoms
        distances = distance_array(chain_a_atoms.positions, 
                                   chain_b_atoms.positions, 
                                   box=universe.dimensions if hasattr(universe, 'dimensions') and universe.dimensions is not None else None)
        
        # Find minimum distance for each chain A atom to any chain B atom
        min_distances_a = np.min(distances, axis=1)
        # Find atoms in chain A within cutoff
        close_atoms_a = chain_a_atoms[min_distances_a <= cutoff]
        
        # Find minimum distance for each chain B atom to any chain A atom
        min_distances_b = np.min(distances, axis=0)
        # Find atoms in chain B within cutoff
        close_atoms_b = chain_b_atoms[min_distances_b <= cutoff]
        
        # Add residues to keep list
        for atom in close_atoms_a:
            res = atom.residue
            global_keep_list.add((chain_a, res.resnum))
        
        for atom in close_atoms_b:
            res = atom.residue
            global_keep_list.add((chain_b, res.resnum))
    
    return global_keep_list, chain_a_atoms, chain_b_atoms

def write_summary_log(input_pdb, output_pdb, log_file, chain_a, chain_b, cutoff, 
                     num_frames, chain_a_atoms, chain_b_atoms, keep_list, 
                     total_atoms, preserved_atoms, deleted_atoms):
    """
    Write a comprehensive summary log to a text file.
    
    Parameters:
    -----------
    input_pdb : str
        Path to input PDB file
    output_pdb : str
        Path to output PDB file
    log_file : str
        Path to log file to write
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    cutoff : float
        Distance cutoff used
    num_frames : int
        Number of frames in the trajectory
    chain_a_atoms : int
        Number of atoms in chain A
    chain_b_atoms : int
        Number of atoms in chain B
    keep_list : set
        Set of (chain_id, residue_id) tuples that were preserved
    total_atoms : int
        Total atoms in both chains
    preserved_atoms : int
        Number of atoms preserved
    deleted_atoms : int
        Number of atoms deleted
    """
    with open(log_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("INTERFACE SELECTION SUMMARY\n")
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
        f.write(f"Chain A:         {chain_a}\n")
        f.write(f"Chain B:         {chain_b}\n")
        f.write(f"Distance cutoff: {cutoff} Å\n")
        f.write(f"Number of frames: {num_frames}\n\n")
        
        # Chain statistics
        f.write("CHAIN STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Chain {chain_a} atoms: {chain_a_atoms}\n")
        f.write(f"Chain {chain_b} atoms: {chain_b_atoms}\n")
        f.write(f"Total atoms in chains {chain_a} and {chain_b}: {total_atoms}\n\n")
        
        # Interface residues
        f.write("INTERFACE RESIDUES\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total unique interface residues found: {len(keep_list)}\n\n")
        
        # Sort residues by chain and residue number for better readability
        sorted_residues = sorted(keep_list, key=lambda x: (x[0], x[1]))
        
        # Group by chain
        chain_a_residues = [res for res in sorted_residues if res[0] == chain_a]
        chain_b_residues = [res for res in sorted_residues if res[0] == chain_b]
        
        f.write(f"Chain {chain_a} interface residues ({len(chain_a_residues)}):\n")
        if chain_a_residues:
            res_nums = [str(res[1]) for res in chain_a_residues]
            # Format as comma-separated list, with line breaks for long lists
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
        
        # Atom statistics
        f.write("ATOM STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total atoms in chains {chain_a} and {chain_b}: {total_atoms}\n")
        f.write(f"Preserved atoms: {preserved_atoms}\n")
        f.write(f"Deleted atoms: {deleted_atoms}\n")
        if total_atoms > 0:
            preservation_percentage = (preserved_atoms / total_atoms) * 100
            deletion_percentage = (deleted_atoms / total_atoms) * 100
            f.write(f"Preservation rate: {preservation_percentage:.2f}%\n")
            f.write(f"Deletion rate: {deletion_percentage:.2f}%\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF SUMMARY\n")
        f.write("=" * 80 + "\n")

def main(input_pdb, output_pdb, chain_a, chain_b, cutoff=7.0):
    """
    Main function to extract interface residues from a multi-model PDB file.
    
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
        Distance cutoff in Angstroms (default: 7.0)
    """
    # Load the structure/trajectory
    universe = mda.Universe(input_pdb)
    
    num_frames = len(universe.trajectory)
    print(f"Loaded structure with {num_frames} frame(s)")
    print(f"Scanning frames for interface residues (cutoff: {cutoff} Å)...")
    
    # Count total atoms in the chains being analyzed
    # Try to get all atoms from both chains
    total_atoms_sel = universe.select_atoms(f"segid {chain_a} or segid {chain_b}")
    if len(total_atoms_sel) == 0:
        # Fallback: try without segid filter
        try:
            all_protein = universe.select_atoms("protein")
            total_atoms_sel = all_protein[(all_protein.segids == chain_a) | (all_protein.segids == chain_b)]
        except:
            total_atoms_sel = universe.select_atoms(f"segid {chain_a} or segid {chain_b}")
    
    total_atoms = len(total_atoms_sel)
    
    # Find interface residues across all frames
    keep_list, chain_a_atoms_obj, chain_b_atoms_obj = find_global_interface(universe, chain_a, chain_b, cutoff)
    chain_a_atoms_count = len(chain_a_atoms_obj)
    chain_b_atoms_count = len(chain_b_atoms_obj)
    print(f"Total unique interface residues found: {len(keep_list)}")
    
    # Create selection string for residues to keep
    # Format: (segid CHAIN and resid RESNUM) or (segid CHAIN and resid RESNUM) ...
    selections = []
    for chain_id, resnum in keep_list:
        selections.append(f"(segid {chain_id} and resid {resnum})")
    
    if not selections:
        print("Warning: No interface residues found. Output file will be empty.")
        preserved_atoms = 0
        deleted_atoms = total_atoms
        # Create empty universe with same topology
        empty_sel = universe.select_atoms("none")
        empty_sel.write(output_pdb)
    else:
        selection_string = " or ".join(selections)
        interface_atoms = universe.select_atoms(selection_string)
        preserved_atoms = len(interface_atoms)
        deleted_atoms = total_atoms - preserved_atoms
        
        # Write the selected atoms to output PDB
        # For multi-model PDBs, write all frames
        if len(universe.trajectory) > 1:
            # Write all frames to the output file
            # MDAnalysis PDBWriter handles multi-model PDBs
            with mda.Writer(output_pdb, interface_atoms.n_atoms) as writer:
                for ts in universe.trajectory:
                    writer.write(interface_atoms)
        else:
            interface_atoms.write(output_pdb)
    
    # Generate log file name based on output PDB name
    log_file = os.path.splitext(output_pdb)[0] + "_summary.txt"
    
    # Write summary to log file
    write_summary_log(input_pdb, output_pdb, log_file, chain_a, chain_b, cutoff,
                     num_frames, chain_a_atoms_count, chain_b_atoms_count, keep_list,
                     total_atoms, preserved_atoms, deleted_atoms)
    
    # Print atom statistics
    print(f"\nAtom Statistics:")
    print(f"  Total atoms in chains {chain_a} and {chain_b}: {total_atoms}")
    print(f"  Preserved atoms: {preserved_atoms}")
    print(f"  Deleted atoms: {deleted_atoms}")
    if total_atoms > 0:
        preservation_percentage = (preserved_atoms / total_atoms) * 100
        print(f"  Preservation rate: {preservation_percentage:.2f}%")
    
    print(f"\nOptimized PDB saved to: {output_pdb}")
    print(f"Summary log saved to: {log_file}")

if __name__ == "__main__":
    # Usage: python interface_selector_mda.py input.pdb optimized.pdb A B [cutoff]
    if len(sys.argv) < 5:
        print("Usage: python interface_selector_mda.py <input.pdb> <output.pdb> <chain1> <chain2> [cutoff]")
        print("  cutoff: optional distance cutoff in Angstroms (default: 7.0)")
    else:
        cutoff = float(sys.argv[5]) if len(sys.argv) > 5 else 7.0
        main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], cutoff)

