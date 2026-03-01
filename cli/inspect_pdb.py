"""
PDB inspection utilities — detect frames and chains from a PDB file.
"""
import MDAnalysis as mda


def inspect_pdb(pdb_path: str) -> dict:
    """
    Inspect a PDB file to detect the number of frames and chain identifiers.

    Handles PDB files with variable atom counts across frames by counting
    MODEL records directly and loading only the first frame for metadata.

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
    # Count frames by MODEL records (handles variable atom counts)
    model_count = 0
    with open(pdb_path, 'r') as fh:
        for line in fh:
            if line[:6].strip() == 'MODEL':
                model_count += 1

    # If no MODEL records, it's a single-frame PDB
    total_frames = model_count if model_count > 0 else 1

    # Load only the first frame for atom/residue/chain info
    # For multi-model files with varying atoms, extract the first frame text
    if model_count > 0:
        first_frame_lines = []
        with open(pdb_path, 'r') as fh:
            in_model = False
            for line in fh:
                record = line[:6].strip()
                if record == 'MODEL':
                    in_model = True
                    continue
                elif record == 'ENDMDL':
                    break
                elif in_model:
                    first_frame_lines.append(line)
        # Write to a temp file for MDAnalysis
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix='.pdb', delete=False, mode='w')
        try:
            tmp.writelines(first_frame_lines)
            tmp.write('END\n')
            tmp.close()
            u = mda.Universe(tmp.name)
        finally:
            os.unlink(tmp.name)
    else:
        u = mda.Universe(pdb_path)

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
