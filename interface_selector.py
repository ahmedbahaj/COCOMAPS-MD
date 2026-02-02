#!/usr/bin/env python3
"""
Interface Selector - Pure Selection Logic

Provides functions to select interface residues between two protein chains 
AND water molecules that bridge both chains.

This module contains ONLY selection logic - no file I/O.
All file operations should be handled by the calling code (analyze_pdb.py).
"""

import numpy as np
from MDAnalysis.analysis.distances import distance_array


# Metal residue names (found in HETATM records)
METALS = set([
    "3CO", "LI", "BE", "NA", "MG", "AL", "K", "CA", "SC", "TI", "V", "CR", "MN",
    "FE", "CO", "NI", "CU", "ZN", "GA", "RB", "SR", "Y", "ZR", "NB", "MO", "TC",
    "RU", "RH", "PD", "AG", "CD", "IN", "SN", "CS", "BA", "LA", "CE", "PR", "ND",
    "PM", "SM", "EU", "GD", "TB", "DY", "HO", "ER", "TM", "YB", "LU", "HF", "TA",
    "W", "RE", "OS", "IR", "PT", "AU", "HG", "TL", "PB", "BI", "PO", "FR", "RA",
    "AC", "TH", "PA", "NP", "PU", "AM", "CM", "BK", "CF"
])


def get_atom_selections(universe, chain_a='A', chain_b='B'):
    """
    Pre-select atom groups for interface and water analysis.
    These selections can be reused across frames (positions auto-update).
    
    Parameters:
    -----------
    universe : MDAnalysis.Universe
        The loaded universe
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    
    Returns:
    --------
    dict : Dictionary containing atom selections:
        - chain_a_atoms: All non-water/ion/metal atoms in chain A
        - chain_b_atoms: All non-water/ion/metal atoms in chain B
        - chain_a_heavy: Heavy atoms in chain A (for water/metal bridging)
        - chain_b_heavy: Heavy atoms in chain B (for water/metal bridging)
        - water_oxygens: Water oxygen atoms
        - metal_atoms: Metal atoms (HETATM with metal residue names)
    """
    # Exclude water and non-metal ions from chain selections
    # Note: Metals are handled separately, only exclude non-metal ions like CL
    water_resnames = "HOH WAT TIP3 SOL"
    non_metal_ions = "CL"
    # Build metal exclusion string from METALS set
    metal_resnames = " ".join(METALS)
    exclude_selection = f"not resname {water_resnames} {non_metal_ions} {metal_resnames}"
    
    # Select chain atoms
    chain_a_atoms = universe.select_atoms(f"segid {chain_a} and {exclude_selection}")
    chain_b_atoms = universe.select_atoms(f"segid {chain_b} and {exclude_selection}")
    
    # Fallback if segid doesn't work
    if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
        chain_a_atoms = universe.select_atoms(f"segid {chain_a}")
        chain_b_atoms = universe.select_atoms(f"segid {chain_b}")
    
    # Heavy atoms for water bridging
    chain_a_heavy = universe.select_atoms(f"segid {chain_a} and {exclude_selection} and not name H*")
    chain_b_heavy = universe.select_atoms(f"segid {chain_b} and {exclude_selection} and not name H*")
    
    if len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        chain_a_heavy = universe.select_atoms(f"segid {chain_a} and not name H*")
        chain_b_heavy = universe.select_atoms(f"segid {chain_b} and not name H*")
    
    # Water oxygens - try multiple naming conventions
    try:
        water_oxygens = universe.select_atoms(
            "(resname HOH and (name O or name OW or name OH2)) or "
            "(resname WAT and (name O or name OW or name OH2)) or "
            "(resname TIP3 and (name O or name OW or name OH2)) or "
            "(resname SOL and (name O or name OW or name OH2))"
        )
    except:
        water_oxygens = universe.select_atoms("resname HOH or resname WAT or resname TIP3 or resname SOL")
    
    # Metal atoms - select atoms with resnames in METALS set
    metal_selection_parts = [f"resname {m}" for m in METALS]
    metal_selection_string = " or ".join(metal_selection_parts)
    try:
        metal_atoms = universe.select_atoms(metal_selection_string)
    except:
        metal_atoms = universe.atoms[:0]  # Empty AtomGroup if selection fails
    
    return {
        'chain_a_atoms': chain_a_atoms,
        'chain_b_atoms': chain_b_atoms,
        'chain_a_heavy': chain_a_heavy,
        'chain_b_heavy': chain_b_heavy,
        'water_oxygens': water_oxygens,
        'metal_atoms': metal_atoms
    }


def select_interface_atoms(universe, selections, chain_a='A', chain_b='B', 
                           cutoff=5.0, water_cutoff=5.0):
    """
    Select interface atoms for the CURRENT frame.
    
    This is a pure selection function - no file I/O.
    Call this after setting the universe to the desired frame.
    
    Parameters:
    -----------
    universe : MDAnalysis.Universe
        The loaded universe (should be set to desired frame)
    selections : dict
        Pre-computed atom selections from get_atom_selections()
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    cutoff : float
        Distance cutoff for interface residues in Angstroms
    water_cutoff : float
        Distance cutoff for bridging waters in Angstroms
    
    Returns:
    --------
    dict : Dictionary containing:
        - atoms: AtomGroup of selected interface atoms (protein + waters + metals)
        - stats: Dictionary with selection statistics
    """
    chain_a_atoms = selections['chain_a_atoms']
    chain_b_atoms = selections['chain_b_atoms']
    chain_a_heavy = selections['chain_a_heavy']
    chain_b_heavy = selections['chain_b_heavy']
    water_oxygens = selections['water_oxygens']
    metal_atoms = selections['metal_atoms']
    
    # Find interface residues
    keep_list = _find_interface_residues(
        chain_a_atoms, chain_b_atoms, chain_a, chain_b, cutoff
    )
    
    # Find bridging waters
    bridging_water_resids = _find_bridging_waters(
        chain_a_heavy, chain_b_heavy, water_oxygens, water_cutoff
    )
    
    # Find interface metals (must be close to BOTH chains, like bridging waters)
    interface_metal_resids = _find_interface_metals(
        chain_a_heavy, chain_b_heavy, metal_atoms, water_cutoff
    )
    
    # Build selection for interface protein atoms
    if keep_list:
        protein_selections = [f"(segid {c} and resid {r})" for c, r in keep_list]
        protein_selection_string = " or ".join(protein_selections)
        interface_protein_atoms = universe.select_atoms(protein_selection_string)
    else:
        interface_protein_atoms = universe.atoms[:0]  # Empty AtomGroup
    
    # Build selection for bridging water atoms
    if bridging_water_resids:
        water_resid_str = " ".join(map(str, bridging_water_resids))
        water_selection = f"(resname HOH or resname WAT or resname TIP3 or resname SOL) and resid {water_resid_str}"
        bridging_water_atoms = universe.select_atoms(water_selection)
    else:
        bridging_water_atoms = universe.atoms[:0]  # Empty AtomGroup
    
    # Build selection for interface metal atoms
    if interface_metal_resids:
        metal_resid_str = " ".join(map(str, interface_metal_resids))
        # Build metal resname selection
        metal_resname_parts = [f"resname {m}" for m in METALS]
        metal_resname_selection = "(" + " or ".join(metal_resname_parts) + ")"
        metal_selection = f"{metal_resname_selection} and resid {metal_resid_str}"
        interface_metal_atoms = universe.select_atoms(metal_selection)
    else:
        interface_metal_atoms = universe.atoms[:0]  # Empty AtomGroup
    
    # Combine protein, water, and metal atoms
    atom_groups = [interface_protein_atoms, bridging_water_atoms, interface_metal_atoms]
    non_empty_groups = [g for g in atom_groups if len(g) > 0]
    
    if non_empty_groups:
        output_atoms = non_empty_groups[0]
        for group in non_empty_groups[1:]:
            output_atoms = output_atoms + group
    else:
        output_atoms = universe.atoms[:0]  # Empty AtomGroup
    
    # Return atoms and statistics
    return {
        'atoms': output_atoms,
        'stats': {
            'interface_residues': len(keep_list),
            'protein_atoms': len(interface_protein_atoms),
            'bridging_waters': len(bridging_water_resids),
            'water_atoms': len(bridging_water_atoms),
            'interface_metals': len(interface_metal_resids),
            'metal_atoms': len(interface_metal_atoms),
            'total_atoms': len(output_atoms)
        }
    }


def _find_interface_residues(chain_a_atoms, chain_b_atoms, chain_a, chain_b, cutoff):
    """
    Find interface residues for the CURRENT frame.
    
    Returns:
    --------
    set : Set of (chain_id, residue_number) tuples at interface
    """
    keep_list = set()
    
    if len(chain_a_atoms) == 0 or len(chain_b_atoms) == 0:
        return keep_list
    
    # Calculate all pairwise distances
    distances = distance_array(
        chain_a_atoms.positions,
        chain_b_atoms.positions,
        box=None
    )
    
    # Find chain A atoms close to any chain B atom
    min_distances_a = np.min(distances, axis=1)
    close_mask_a = min_distances_a <= cutoff
    
    # Find chain B atoms close to any chain A atom
    min_distances_b = np.min(distances, axis=0)
    close_mask_b = min_distances_b <= cutoff
    
    # Get residue info for close atoms
    for atom in chain_a_atoms[close_mask_a]:
        keep_list.add((chain_a, atom.residue.resnum))
    
    for atom in chain_b_atoms[close_mask_b]:
        keep_list.add((chain_b, atom.residue.resnum))
    
    return keep_list


def _find_bridging_waters(chain_a_heavy, chain_b_heavy, water_oxygens, cutoff):
    """
    Find bridging water molecules for the CURRENT frame.
    
    A bridging water must be within cutoff of BOTH chain A AND chain B.
    
    Returns:
    --------
    set : Set of water residue IDs that bridge both chains
    """
    if len(water_oxygens) == 0 or len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        return set()
    
    # Calculate distances
    dist_to_a = distance_array(water_oxygens.positions, chain_a_heavy.positions, box=None)
    dist_to_b = distance_array(water_oxygens.positions, chain_b_heavy.positions, box=None)
    
    # Find minimum distance to each chain
    min_dist_to_a = np.min(dist_to_a, axis=1)
    min_dist_to_b = np.min(dist_to_b, axis=1)
    
    # Water must be within cutoff of BOTH chains
    bridging_mask = (min_dist_to_a <= cutoff) & (min_dist_to_b <= cutoff)
    
    # Get residue IDs
    bridging_resids = set()
    for i, water_atom in enumerate(water_oxygens):
        if bridging_mask[i]:
            bridging_resids.add(water_atom.resid)
    
    return bridging_resids


def _find_interface_metals(chain_a_heavy, chain_b_heavy, metal_atoms, cutoff):
    """
    Find interface metal atoms for the CURRENT frame.
    
    A metal is considered at the interface if it is within cutoff of BOTH 
    chain A AND chain B (same criteria as bridging waters).
    
    Parameters:
    -----------
    chain_a_heavy : AtomGroup
        Heavy atoms in chain A
    chain_b_heavy : AtomGroup
        Heavy atoms in chain B
    metal_atoms : AtomGroup
        All metal atoms in the structure
    cutoff : float
        Distance cutoff in Angstroms
    
    Returns:
    --------
    set : Set of metal residue IDs that are at the interface (close to both chains)
    """
    if len(metal_atoms) == 0 or len(chain_a_heavy) == 0 or len(chain_b_heavy) == 0:
        return set()
    
    # Calculate distances from metals to each chain
    dist_to_a = distance_array(metal_atoms.positions, chain_a_heavy.positions, box=None)
    dist_to_b = distance_array(metal_atoms.positions, chain_b_heavy.positions, box=None)
    
    # Find minimum distance to each chain
    min_dist_to_a = np.min(dist_to_a, axis=1)
    min_dist_to_b = np.min(dist_to_b, axis=1)
    
    # Metal must be within cutoff of BOTH chains (like bridging waters)
    interface_mask = (min_dist_to_a <= cutoff) & (min_dist_to_b <= cutoff)
    
    # Get residue IDs
    interface_metal_resids = set()
    for i, metal_atom in enumerate(metal_atoms):
        if interface_mask[i]:
            interface_metal_resids.add(metal_atom.resid)
    
    return interface_metal_resids


def get_selection_summary(selections):
    """
    Get a summary of the atom selections for logging.
    
    Parameters:
    -----------
    selections : dict
        Pre-computed atom selections from get_atom_selections()
    
    Returns:
    --------
    dict : Summary statistics
    """
    return {
        'chain_a_atoms': len(selections['chain_a_atoms']),
        'chain_b_atoms': len(selections['chain_b_atoms']),
        'chain_a_heavy': len(selections['chain_a_heavy']),
        'chain_b_heavy': len(selections['chain_b_heavy']),
        'water_molecules': len(selections['water_oxygens']),
        'metal_atoms': len(selections['metal_atoms'])
    }
