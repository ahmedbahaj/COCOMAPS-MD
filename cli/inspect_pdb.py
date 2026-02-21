"""
PDB inspection utilities — detect frames and chains from a PDB file.
"""
import MDAnalysis as mda


def inspect_pdb(pdb_path: str) -> dict:
    """
    Inspect a PDB file to detect the number of frames and chain identifiers.

    Parameters
    ----------
    pdb_path : str
        Path to the PDB file.

    Returns
    -------
    dict
        {
            'total_frames': int,
            'chains': list[str],   # unique chain IDs, sorted
            'n_atoms': int,
            'n_residues': int,
        }
    """
    u = mda.Universe(pdb_path)

    total_frames = len(u.trajectory)

    # Collect unique chain (segment) IDs
    chain_ids = sorted(set(u.atoms.segids))
    # Fallback: if segids are blank, try chainIDs attribute
    if not chain_ids or chain_ids == ['']:
        try:
            chain_ids = sorted(set(u.atoms.chainIDs))
        except AttributeError:
            chain_ids = []

    return {
        'total_frames': total_frames,
        'chains': chain_ids,
        'n_atoms': len(u.atoms),
        'n_residues': len(u.residues),
    }
