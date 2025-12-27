#!/usr/bin/env python3
"""
Water Molecule Truncation Pre-processor
Efficiently filters water molecules based on proximity to protein chains A and B.
Uses spatial grid hashing for O(N+M) complexity instead of naive O(N*M).
"""

import MDAnalysis as mda
from MDAnalysis.coordinates import PDB
import numpy as np
from pathlib import Path
import argparse
import os

# Default distance threshold in Angstroms
DEFAULT_DISTANCE = 5.0


def truncate_waters(input_pdb, output_pdb=None, distance=DEFAULT_DISTANCE, 
                    chains=None, verbose=True):
    """
    Truncate water molecules that are far from specified protein chains.
    
    Parameters:
    -----------
    input_pdb : str
        Path to input PDB file
    output_pdb : str, optional
        Path to output PDB file. If None, generates from input name
    distance : float
        Distance threshold in Angstroms (default: 5.0)
    chains : list, optional
        List of chain IDs to consider (default: ['A', 'B'])
    verbose : bool
        Print progress information
    
    Returns:
    --------
    str : Path to output PDB file
    """
    if chains is None:
        chains = ['A', 'B']
    
    if verbose:
        print(f"Loading PDB file: {input_pdb}")
    
    # Load the PDB file
    u = mda.Universe(input_pdb)
    
    # Select protein atoms from specified chains
    chain_selection = " or ".join([f"segid {c}" for c in chains])
    if not chain_selection:
        # Try chainID instead of segid
        chain_selection = " or ".join([f"chainID {c}" for c in chains])
    
    try:
        protein_atoms = u.select_atoms(chain_selection)
    except:
        # If segid/chainID doesn't work, try alternative selection
        protein_atoms = u.select_atoms(f"protein and ({chain_selection})")
    
    if len(protein_atoms) == 0:
        if verbose:
            print(f"Warning: No atoms found for chains {chains}")
            print("Trying to select all protein atoms instead...")
        protein_atoms = u.select_atoms("protein")
    
    # Select water molecules (by oxygen atoms)
    try:
        water_oxygens = u.select_atoms(
            "resname HOH and name O or "
            "resname WAT and name O or "
            "resname TIP3 and name OH2 or "
            "resname SOL and name OW"
        )
    except:
        water_oxygens = u.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL")
    
    if verbose:
        print(f"Found {len(protein_atoms)} protein atoms in chains {chains}")
        print(f"Found {len(water_oxygens)} water molecules")
        print(f"Distance threshold: {distance} Å")
        print()
    
    if len(water_oxygens) == 0:
        if verbose:
            print("No water molecules found. Saving file as-is.")
        if output_pdb is None:
            output_pdb = input_pdb.replace('.pdb', '_truncated.pdb')
        
        # Handle multi-frame trajectories
        num_frames = len(u.trajectory)
        if num_frames > 1:
            with PDB.PDBWriter(output_pdb, multiframe=True) as writer:
                for ts in u.trajectory:
                    writer.write(u.atoms)
        else:
            u.atoms.write(output_pdb)
        
        if verbose:
            print(f"  Wrote {num_frames} frames to output")
        return output_pdb
    
    # PHASE 1: Build spatial grid hash for protein atoms
    if verbose:
        print("Phase 1: Building spatial grid for protein atoms...")
    
    grid_size = distance
    occupied_cells = set()
    
    protein_positions = protein_atoms.positions
    
    for pos in protein_positions:
        # Convert 3D coordinates to grid cell indices
        cell_x = int(np.floor(pos[0] / grid_size))
        cell_y = int(np.floor(pos[1] / grid_size))
        cell_z = int(np.floor(pos[2] / grid_size))
        
        # Mark the cell and all 26 neighboring cells
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    neighbor_key = (cell_x + dx, cell_y + dy, cell_z + dz)
                    occupied_cells.add(neighbor_key)
    
    if verbose:
        print(f"  Created {len(occupied_cells)} occupied grid cells")
        print()
    
    # PHASE 2: Filter water molecules
    if verbose:
        print("Phase 2: Filtering water molecules...")
    
    water_positions = water_oxygens.positions
    keep_water_indices = []
    
    for idx, pos in enumerate(water_positions):
        # Get grid cell for water oxygen
        w_cell_x = int(np.floor(pos[0] / grid_size))
        w_cell_y = int(np.floor(pos[1] / grid_size))
        w_cell_z = int(np.floor(pos[2] / grid_size))
        water_key = (w_cell_x, w_cell_y, w_cell_z)
        
        # O(1) hash lookup
        if water_key in occupied_cells:
            keep_water_indices.append(idx)
    
    # Get the actual water residues to keep (including H atoms)
    waters_to_keep = water_oxygens[keep_water_indices]
    # Get all atoms in those residues
    keep_resids = set(waters_to_keep.resids)
    all_waters = u.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL")
    filtered_waters = all_waters.select_atoms(f"resid {' '.join(map(str, keep_resids))}")
    
    if verbose:
        removed = len(water_oxygens) - len(waters_to_keep)
        kept_pct = 100 * len(waters_to_keep) / len(water_oxygens) if len(water_oxygens) > 0 else 0
        print(f"  Kept: {len(waters_to_keep)} water molecules ({kept_pct:.1f}%)")
        print(f"  Removed: {removed} water molecules ({100-kept_pct:.1f}%)")
        print()
    
    # PHASE 3: Create output
    if verbose:
        print("Phase 3: Writing output PDB...")
    
    # Select all non-water atoms + filtered waters
    non_water = u.select_atoms("not (resname HOH or resname WAT or resname TIP3 or resname SOL)")
    output_atoms = non_water + filtered_waters
    
    # Generate output filename if not provided
    if output_pdb is None:
        input_path = Path(input_pdb)
        output_pdb = str(input_path.parent / f"{input_path.stem}_truncated.pdb")
    
    # Write output - handle multi-frame trajectories
    num_frames = len(u.trajectory)
    if num_frames > 1:
        if verbose:
            print(f"  Writing {num_frames} frames...")
        with PDB.PDBWriter(output_pdb, multiframe=True) as writer:
            for ts in u.trajectory:
                writer.write(output_atoms)
    else:
        output_atoms.write(output_pdb)
    
    if verbose:
        print(f"✓ Truncated PDB saved to: {output_pdb}")
        print(f"  Frames: {num_frames}")
        print(f"  Total atoms per frame: {len(non_water)} (non-water) + {len(filtered_waters)} (water) = {len(output_atoms)}")
        print()
    
    return output_pdb


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Truncate water molecules from PDB based on distance to protein chains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default 5Å distance
  python truncate_waters.py input.pdb
  
  # Specify custom distance threshold
  python truncate_waters.py input.pdb -d 7.0
  
  # Specify output file
  python truncate_waters.py input.pdb -o output.pdb
  
  # Custom chains (default is A and B)
  python truncate_waters.py input.pdb -c A B C
        """
    )
    
    parser.add_argument('input_pdb', help='Input PDB file')
    parser.add_argument('-o', '--output', help='Output PDB file (default: input_truncated.pdb)')
    parser.add_argument('-d', '--distance', type=float, default=DEFAULT_DISTANCE,
                       help=f'Distance threshold in Angstroms (default: {DEFAULT_DISTANCE})')
    parser.add_argument('-c', '--chains', nargs='+', default=['A', 'B'],
                       help='Chain IDs to consider (default: A B)')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Suppress progress output')
    
    args = parser.parse_args()
    
    # Check input file exists
    if not os.path.exists(args.input_pdb):
        print(f"Error: Input file '{args.input_pdb}' not found!")
        return 1
    
    # Run truncation
    try:
        output_file = truncate_waters(
            args.input_pdb,
            output_pdb=args.output,
            distance=args.distance,
            chains=args.chains,
            verbose=not args.quiet
        )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

