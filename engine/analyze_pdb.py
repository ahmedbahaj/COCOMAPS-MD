#!/usr/bin/env python3
"""
Complete PDB Analysis Pipeline
1. Process frames (with optional interface selection)
2. Run CoCoMaps analysis on each frame

All file I/O is centralized in this module.
Interface selection logic is delegated to interface_selector.py.
"""

import subprocess
import sys
import os
import time
import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
import MDAnalysis as mda

try:
    from distutils.util import strtobool
except ImportError:
    def strtobool(val):
        val = str(val).lower().strip()
        if val in ('y', 'yes', 't', 'true', '1', 'on'):
            return 1
        if val in ('n', 'no', 'f', 'false', '0', 'off'):
            return 0
        raise ValueError(f"invalid truth value: {val!r}")
from MDAnalysis.coordinates import PDB
from dotenv import load_dotenv

# Load .env from project root (parent of engine/)
_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(_env_path)

# Import pure selection functions from interface_selector
from .interface_selector import (
    get_atom_selections,
    select_interface_atoms,
    get_selection_summary
)

# CoCoMaps local package path (sibling of engine/)
COCOMAPS_DIR = Path(__file__).resolve().parent.parent / 'cocomaps'

USE_REDUCE = bool(strtobool(os.environ.get("COCOMAPS_USE_REDUCE", "false")))
INPUT_FILE_NAME = os.environ.get("INPUT_FILE_NAME", "example_input.json")

# Default parameters (loaded from .env or defaults)
DEFAULT_INTERFACE_CUTOFF = float(os.environ.get("DEFAULT_INTERFACE_CUTOFF", "5.0"))
SELECT_INTERFACE = bool(strtobool(os.environ.get("SELECT_INTERFACE", "true")))
_chains_env = os.environ.get("DEFAULT_CHAINS", "A,B")
DEFAULT_CHAINS = [c.strip() for c in _chains_env.split(',')]


def rename_waters_to_hoh(atoms):
    """
    Rename all water residues (SOL, WAT, TIP3) to HOH for CoCoMaps compatibility.
    
    CoCoMaps only recognizes HOH as water residues. This function converts
    other common water naming conventions to HOH.
    
    Parameters:
    -----------
    atoms : MDAnalysis.AtomGroup or Universe
        The atoms to process (modifies residue names in-place)
    """
    water_resnames_to_convert = ['SOL', 'WAT', 'TIP3']
    
    for residue in atoms.residues:
        if residue.resname in water_resnames_to_convert:
            residue.resname = 'HOH'


def process_frames(pdb_file, output_dir, chain_a='A', chain_b='B',
                   select_interface=False, cutoff=5.0, water_cutoff=5.0,
                   verbose=True, step_num=None, start_frame=0, end_frame=-1, frame_step=1):
    """
    Process PDB file: split into frames with optional interface selection.
    
    This is the unified frame processing function that handles all file I/O.
    
    Parameters:
    -----------
    pdb_file : str
        Path to input PDB file (can be multi-model/trajectory)
    output_dir : str
        Output directory. Creates frame_N/frame_N.pdb for each frame.
    chain_a : str
        Chain identifier for the first chain
    chain_b : str
        Chain identifier for the second chain
    select_interface : bool
        If True, keep only interface residues and bridging waters.
        If False, keep all atoms.
    cutoff : float
        Distance cutoff for interface residues in Angstroms
    water_cutoff : float
        Distance cutoff for bridging waters in Angstroms
    verbose : bool
        Whether to print progress messages
    step_num : int or None
        Step number for display (e.g., "STEP 1:")
    start_frame : int
        0-based index of first frame to process (default 0)
    end_frame : int
        0-based exclusive end index, or -1 for all frames (default -1)
    frame_step : int
        Step between frames (default 1)
    
    Returns:
    --------
    tuple : (output_dir, frame_count, frame_stats)
    """
    step_label = f"STEP {step_num}: " if step_num else ""
    
    if verbose:
        print(f"\n{'='*80}")
        if select_interface:
            print(f"{step_label}Processing frames with interface selection")
        else:
            print(f"{step_label}Splitting PDB into frames")
        print(f"{'='*80}")
        print(f"Input PDB: {pdb_file}")
        print(f"Output Directory: {output_dir}")
        if select_interface:
            print(f"Chains: {chain_a}, {chain_b}")
            print(f"Interface cutoff: {cutoff} Å")
            print(f"Water cutoff: {water_cutoff} Å")
            print(f"Mode: Per-frame interface selection")
        else:
            print(f"Mode: Full structure (all atoms)")
    
    start_time = time.time()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy original PDB to output directory
    original_name = Path(pdb_file).name
    dest_path = os.path.join(output_dir, original_name)
    if not os.path.exists(dest_path):
        shutil.copy(pdb_file, dest_path)
        if verbose:
            print(f"Copied original PDB to: {dest_path}")
    
    # ── Split the PDB into raw per-frame text blocks ──
    # Handles both MODEL/ENDMDL-delimited and END-delimited multi-frame PDBs.
    import tempfile as _tmpmod

    raw_frames = []  # list of frame text strings
    with open(pdb_file, 'r') as fh:
        current_frame_lines = []
        in_model = False
        for line in fh:
            record = line[:6].strip()
            if record == 'MODEL':
                in_model = True
                current_frame_lines = [line]
            elif record == 'ENDMDL':
                current_frame_lines.append(line)
                raw_frames.append(''.join(current_frame_lines))
                current_frame_lines = []
                in_model = False
            elif in_model:
                current_frame_lines.append(line)

    if not raw_frames:
        # Fallback: split by END records (multi-frame without MODEL/ENDMDL)
        with open(pdb_file, 'r') as fh:
            current_frame_lines = []
            for line in fh:
                record = line[:6].strip()
                if record == 'END':
                    if current_frame_lines:
                        raw_frames.append(''.join(current_frame_lines))
                        current_frame_lines = []
                else:
                    current_frame_lines.append(line)
            if current_frame_lines:
                raw_frames.append(''.join(current_frame_lines))

    num_frames = len(raw_frames)
    if end_frame == -1 or end_frame > num_frames:
        end_frame = num_frames
    if start_frame < 0:
        start_frame = 0
    frame_step = max(1, frame_step)
    frames_to_process = list(range(start_frame, end_frame, frame_step))
    num_to_process = len(frames_to_process)

    if verbose:
        print(f"Loaded structure with {num_frames} frame(s)")
        if num_to_process != num_frames:
            print(f"Processing frames {start_frame + 1} to {end_frame} (step {frame_step}) -> {num_to_process} frames")

    # Load first frame to process for chain/atom info for display
    first_idx = frames_to_process[0] if frames_to_process else 0
    _tmp_first = _tmpmod.NamedTemporaryFile(suffix='.pdb', delete=False, mode='w')
    _tmp_first.write(raw_frames[first_idx])
    if not raw_frames[first_idx].rstrip().endswith('END'):
        _tmp_first.write('END\n')
    _tmp_first.close()
    _first_universe = mda.Universe(_tmp_first.name)

    # Pre-compute atom selections if doing interface selection (from first frame)
    selections = None
    if select_interface:
        selections = get_atom_selections(_first_universe, chain_a, chain_b)
        summary = get_selection_summary(selections)
        if verbose:
            print(f"Chain {chain_a}: {summary['chain_a_atoms']} atoms, {summary['chain_a_heavy']} heavy atoms")
            print(f"Chain {chain_b}: {summary['chain_b_atoms']} atoms, {summary['chain_b_heavy']} heavy atoms")
            print(f"Total water molecules: {summary['water_molecules']}")
            print(f"Total metal atoms: {summary['metal_atoms']}")
    _first_universe.trajectory.close()
    del _first_universe
    os.unlink(_tmp_first.name)

    if verbose:
        print(f"\nProcessing frames...")

    # Track statistics
    frame_stats = []

    # Process each frame from raw text (only frames in frames_to_process)
    for out_idx, frame_idx in enumerate(frames_to_process):
        frame_num = out_idx + 1
        raw_text = raw_frames[frame_idx]

        # Write raw frame to a temp file and load it
        tmp_frame = _tmpmod.NamedTemporaryFile(suffix='.pdb', delete=False, mode='w')
        tmp_frame.write(raw_text)
        if not raw_text.rstrip().endswith('END'):
            tmp_frame.write('END\n')
        tmp_frame.close()
        universe = mda.Universe(tmp_frame.name)

        if select_interface:
            # Re-compute selections for this frame's universe
            frame_selections = get_atom_selections(universe, chain_a, chain_b)
            result = select_interface_atoms(
                universe, frame_selections, chain_a, chain_b, cutoff, water_cutoff
            )
            output_atoms = result['atoms']
            stats = result['stats']
        else:
            # Keep all atoms
            output_atoms = universe.atoms
            stats = {
                'interface_residues': len(universe.residues),
                'protein_atoms': len(universe.atoms),
                'bridging_waters': 0,
                'water_atoms': 0,
                'interface_metals': 0,
                'metal_atoms': 0,
                'total_atoms': len(universe.atoms)
            }

        # === CENTRALIZED WRITE POINT ===
        # All PDB writing happens here - perfect place for transformations

        # Rename waters to HOH for CoCoMaps compatibility
        rename_waters_to_hoh(output_atoms)

        # Create frame directory and write PDB
        frame_folder = os.path.join(output_dir, f"frame_{frame_num}")
        os.makedirs(frame_folder, exist_ok=True)
        frame_file = os.path.join(frame_folder, f"frame_{frame_num}.pdb")

        if len(output_atoms) > 0:
            output_atoms.write(frame_file)
        else:
            # Write empty PDB file header only
            with open(frame_file, 'w') as f:
                f.write("REMARK   Empty frame - no interface atoms found\nEND\n")

        # Close the trajectory reader so Windows releases the file lock
        universe.trajectory.close()
        del universe
        os.unlink(tmp_frame.name)

        # Track statistics
        stats['frame'] = frame_num
        frame_stats.append(stats)

        if verbose:
            if select_interface:
                print(f"  Frame {frame_num}: {stats['interface_residues']} residues, "
                      f"{stats['protein_atoms']} protein atoms, "
                      f"{stats['bridging_waters']} waters, "
                      f"{stats['interface_metals']} metals → {stats['total_atoms']} total atoms")
            else:
                print(f"  Frame {frame_num}: {stats['total_atoms']} atoms")
    
    elapsed = time.time() - start_time
    
    # Write summary log if interface selection was used
    if select_interface:
        log_file = os.path.join(output_dir, "interface_selection_summary.txt")
        _write_summary_log(
            pdb_file, output_dir, log_file, chain_a, chain_b, cutoff, water_cutoff,
            num_to_process, selections, frame_stats
        )
        if verbose:
            print(f"\nSummary log: {log_file}")
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Frame Processing Complete")
        print(f"{'='*60}")
        print(f"Frames processed: {num_to_process}")
        print(f"Time elapsed: {elapsed:.2f} seconds")
        if select_interface and frame_stats:
            avg_residues = sum(s['interface_residues'] for s in frame_stats) / len(frame_stats)
            avg_total = sum(s['total_atoms'] for s in frame_stats) / len(frame_stats)
            print(f"Average interface residues: {avg_residues:.1f}")
            print(f"Average total atoms: {avg_total:.1f}")
        print(f"Output directory: {output_dir}")
    
    return output_dir, num_to_process, frame_stats


def _write_summary_log(input_pdb, output_dir, log_file, chain_a, chain_b,
                       cutoff, water_cutoff, num_frames, selections, frame_stats):
    """Write a summary log for interface selection."""
    summary = get_selection_summary(selections)
    
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
        f.write(f"Chain {chain_a} atoms: {summary['chain_a_atoms']}\n")
        f.write(f"Chain {chain_b} atoms: {summary['chain_b_atoms']}\n")
        f.write(f"Total water molecules: {summary['water_molecules']}\n")
        f.write(f"Total metal atoms: {summary['metal_atoms']}\n\n")
        
        f.write("PER-FRAME STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Frame':<8} {'Residues':<10} {'Protein':<10} {'Waters':<10} {'Metals':<10} {'Total':<10}\n")
        f.write("-" * 80 + "\n")
        
        for s in frame_stats:
            f.write(f"{s['frame']:<8} {s['interface_residues']:<10} "
                    f"{s['protein_atoms']:<10} {s['bridging_waters']:<10} "
                    f"{s['interface_metals']:<10} {s['total_atoms']:<10}\n")
        
        f.write("-" * 80 + "\n")
        
        # Averages
        avg_residues = sum(s['interface_residues'] for s in frame_stats) / num_frames
        avg_protein = sum(s['protein_atoms'] for s in frame_stats) / num_frames
        avg_waters = sum(s['bridging_waters'] for s in frame_stats) / num_frames
        avg_metals = sum(s['interface_metals'] for s in frame_stats) / num_frames
        avg_total = sum(s['total_atoms'] for s in frame_stats) / num_frames
        
        f.write(f"{'Average':<8} {avg_residues:<10.1f} {avg_protein:<10.1f} "
                f"{avg_waters:<10.1f} {avg_metals:<10.1f} {avg_total:<10.1f}\n\n")
        
        # Min/Max
        min_atoms = min(s['total_atoms'] for s in frame_stats)
        max_atoms = max(s['total_atoms'] for s in frame_stats)
        f.write(f"Minimum atoms in a frame: {min_atoms}\n")
        f.write(f"Maximum atoms in a frame: {max_atoms}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF SUMMARY\n")
        f.write("=" * 80 + "\n")


def create_input_jsons(output_dir, frame_count, chains=None, interface_cutoff=5.0, use_reduce=False):
    """Create example_input.json files for each frame.

    ``use_reduce`` is written into the JSON as ``REDUCE_BOOL`` so the
    local CoCoMaps package enables/disables hydrogen addition accordingly.
    """
    if chains is None:
        chains = DEFAULT_CHAINS
    
    print(f"\nCreating input JSON files for {frame_count} frames...")
    
    for i in range(1, frame_count + 1):
        frame_folder = os.path.join(output_dir, f"frame_{i}")
        json_file = os.path.join(frame_folder, INPUT_FILE_NAME)
        pdb_path = os.path.abspath(os.path.join(frame_folder, f"frame_{i}.pdb"))
        
        json_data = {
            "pdb_file": pdb_path,
            "REDUCE_BOOL": use_reduce,
            "chains_set_1": chains[:1],
            "chains_set_2": chains[1:2] if len(chains) > 1 else chains[:1],
            "ranges_1": [[0, 100000]],
            "ranges_2": [[0, 100000], [0, 100000]],
            "HBOND_DIST": 3.9,
            "HBOND_ANGLE": 90,
            "SBRIDGE_DIST": 4.5,
            "WBRIDGE_DIST": 3.9,
            "CH_ON_DIST": 3.6,
            "CH_ON_ANGLE": 110,
            "CUT_OFF": interface_cutoff,
            "APOLAR_TOLERANCE": 0.5,
            "POLAR_TOLERANCE": 0.5,
            "PI_PI_DIST": 5.5,
            "PI_PI_THETA": 80,
            "PI_PI_GAMMA": 90,
            "ANION_PI_DIST": 5,
            "LONEPAIR_PI_DIST": 5,
            "AMINO_PI_DIST": 5,
            "CATION_PI_DIST": 5,
            "METAL_DIST": 3.2,
            "HALOGEN_THETA1": 165,
            "HALOGEN_THETA2": 120,
            "C_H_PI_DIST": 5.0,
            "C_H_PI_THETA1": 120,
            "C_H_PI_THETA2": 30,
            "NSOH_PI_DIST": 4.5,
            "NSOH_PI_THETA1": 120,
            "NSOH_PI_THETA2": 30
        }
        
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=4)
    
    print(f"✓ Created {frame_count} input JSON files")


def run_cocomaps_analysis(output_dir, use_reduce=False, step_num=None, progress_callback=None):
    """Run CoCoMaps analysis locally on all frames.

    Uses the local ``cocomaps/begin.py`` script (extracted from the
    sattamaltwaim/cocomaps-backend Docker image) instead of Docker.
    The ``REDUCE_BOOL`` flag in each frame's input JSON controls
    whether hydrogen addition is performed.

    progress_callback: optional callable(step_label, progress_pct) called per frame.
    """
    step_label = f"STEP {step_num}: " if step_num else ""
    print(f"\n{'='*80}")
    print(f"{step_label}Running CoCoMaps Analysis ({'WITH' if use_reduce else 'WITHOUT'} reduce)")
    print(f"{'='*80}")
    
    begin_py = str(COCOMAPS_DIR / 'begin.py')
    print(f"CoCoMaps script: {begin_py}\n")
    
    # Get frame numbers
    frame_numbers = []
    for item in Path(output_dir).iterdir():
        if item.is_dir() and item.name.startswith('frame_'):
            try:
                frame_num = int(item.name.split('_')[1])
                frame_numbers.append(frame_num)
            except (IndexError, ValueError):
                pass
    
    frame_numbers = sorted(frame_numbers)
    total = len(frame_numbers)
    print(f"Found {total} frames to process\n")
    
    start_time = time.time()
    successful = 0
    failed = 0
    
    for idx, i in enumerate(frame_numbers):
        if progress_callback:
            progress_callback(step_label=f'Analyzing frame {idx + 1}/{total}', progress=30 + int((idx + 1) / total * 60))

        frame_folder = f"frame_{i}"
        frame_path = os.path.join(output_dir, frame_folder)
        input_json = os.path.abspath(os.path.join(frame_path, INPUT_FILE_NAME))

        command = [sys.executable, begin_py, input_json]
        
        print(f"Processing frame {i}...", end=" ", flush=True)
        
        try:
            subprocess.run(
                command, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                cwd=frame_path,
            )
            print("✓")
            successful += 1
        except subprocess.CalledProcessError as e:
            print("✗")
            print(f"  Error: {(e.output or '')[:200]}")
            failed += 1
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print("CoCoMaps Analysis Complete")
    print(f"{'='*80}")
    print(f"Successful: {successful}/{len(frame_numbers)}")
    print(f"Failed: {failed}/{len(frame_numbers)}")
    print(f"Total time: {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
    if frame_numbers:
        print(f"Average time per frame: {elapsed/len(frame_numbers):.2f} seconds")
    
    return elapsed, successful, failed


def run_pipeline(
    pdb_file,
    output_dir,
    chain_a='A',
    chain_b='B',
    interface_cutoff=5.0,
    water_cutoff=None,
    use_reduce=False,
    start_frame=0,
    end_frame=-1,
    frame_step=1,
    progress_callback=None,
    verbose=True,
):
    """
    Run the full analysis pipeline (engine entry point).
    Used by both the CLI (main) and the web backend.

    progress_callback: optional callable(step_label, progress_pct) for UI updates (e.g. web job status).
    Returns: (frame_count, None) on success, or (0, error_message) on failure.
    """
    if water_cutoff is None:
        water_cutoff = interface_cutoff
    try:
        if progress_callback:
            progress_callback(step_label='Preprocessing file', progress=0)

        output_dir, frame_count, frame_stats = process_frames(
            pdb_file,
            output_dir,
            chain_a=chain_a,
            chain_b=chain_b,
            select_interface=True,
            cutoff=interface_cutoff,
            water_cutoff=water_cutoff,
            verbose=verbose,
            start_frame=start_frame,
            end_frame=end_frame,
            frame_step=frame_step,
        )

        if frame_count == 0:
            return 0, 'No frames to process. Check MODEL/ENDMDL/END records and selected chains.'

        if frame_stats and all(s.get('total_atoms', 0) == 0 for s in frame_stats):
            return 0, f'No interface atoms in any frame. Check chain IDs (e.g. 1ULL uses A and B).'

        create_input_jsons(output_dir, frame_count, [chain_a, chain_b], interface_cutoff=interface_cutoff, use_reduce=use_reduce)

        _, successful, failed = run_cocomaps_analysis(
            output_dir, use_reduce=use_reduce, step_num=None, progress_callback=progress_callback
        )

        if successful == 0 and failed > 0:
            return 0, (
                f'CoCoMaps analysis failed for all {failed} frame(s). '
                f'Check that the cocomaps/ package and deps/ binaries are present '
                f'and that the required Python dependencies (biopython, scipy) are installed.'
            )

        if failed > 0:
            print(f'[pipeline] Warning: {failed}/{successful + failed} frames failed CoCoMaps analysis and will be skipped.')

        if progress_callback:
            progress_callback(step_label='Running conserved island analysis', progress=92)

        from .conserved_islands import run_conserved_islands
        run_conserved_islands(
            output_dir,
            min_consistency=0.70,
            min_island_size=2,
            verbose=verbose,
        )

        if progress_callback:
            progress_callback(step_label='Aggregating results', progress=96)

        from .aggregate_csv import aggregate_system
        aggregate_system(output_dir, verbose=verbose)

        if progress_callback:
            progress_callback(step_label='Completed', progress=100)

        return frame_count, None
    except Exception as e:
        return 0, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Complete PDB analysis pipeline with interface selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (interface selection is always on)
  python -m engine.analyze_pdb systems/my_protein.pdb

  # Interface selection with custom cutoff (default: 5Å)
  python -m engine.analyze_pdb systems/my_protein.pdb --interface-cutoff 7.0

  # Separate cutoffs for protein interface and water bridges
  python -m engine.analyze_pdb systems/my_protein.pdb --interface-cutoff 5.0 --water-cutoff 3.5

  # Enable reduce (adds hydrogens, slower)
  python -m engine.analyze_pdb systems/my_protein.pdb --use-reduce

  # Custom output directory
  python -m engine.analyze_pdb systems/my_protein.pdb -o systems/my_output

Interface Selection (always on):
  Each frame is processed with per-frame interface selection:
  - Only residues within cutoff distance of the partner chain IN THAT FRAME are kept
  - Bridging waters (within cutoff of BOTH chains) are also kept per-frame

Note: All water residues (SOL, WAT, TIP3, etc.) are automatically renamed to HOH
for CoCoMaps compatibility.

Environment Variables:
  SELECT_INTERFACE=true/false    - Enable/disable interface selection (default: true)
  COCOMAPS_USE_REDUCE=true/false - Enable/disable reduce (default: false)
  COCOMAPS_DEPS_DIR              - Path to binary deps (reduce, hbplus, naccess)
  DEFAULT_INTERFACE_CUTOFF       - Interface/water cutoff in Angstroms (default: 5.0)
        """
    )
    
    parser.add_argument('pdb_file', help='Input PDB file to analyze')
    parser.add_argument('-o', '--output', help='Output directory (default: systems/<pdb_name>)')
    parser.add_argument('--use-reduce', dest='use_reduce', action='store_true',
                       help='Use reduce version of CoCoMaps')
    parser.add_argument('--no-reduce', dest='use_reduce', action='store_false',
                       help='Use no-reduce version of CoCoMaps')
    parser.add_argument('-c', '--chains', nargs='+', default=DEFAULT_CHAINS,
                       help='Chain IDs to analyze (default: A B)')
    
    # Interface selection (always on; cutoff is configurable)
    parser.add_argument('--interface-cutoff', type=float, default=DEFAULT_INTERFACE_CUTOFF,
                       help=f'Interface selection cutoff in Angstroms (default: {DEFAULT_INTERFACE_CUTOFF})')
    parser.add_argument('--water-cutoff', type=float, default=None,
                       help=f'Bridging water cutoff in Angstroms (default: same as interface-cutoff)')
    
    # Set defaults from environment variables (interface selection always on)
    parser.set_defaults(use_reduce=USE_REDUCE, select_interface=True)
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.pdb_file):
        print(f"Error: PDB file not found: {args.pdb_file}")
        return 1
    
    # Use interface cutoff for water if not specified
    water_cutoff = args.water_cutoff if args.water_cutoff is not None else args.interface_cutoff
    
    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        pdb_stem = Path(args.pdb_file).stem
        if args.pdb_file.startswith('systems/'):
            output_dir = os.path.join('systems', pdb_stem)
        else:
            output_dir = pdb_stem
    
    # Print pipeline summary
    print(f"\n{'='*80}")
    print("PDB ANALYSIS PIPELINE")
    print(f"{'='*80}")
    print(f"Input PDB: {args.pdb_file}")
    print(f"Output Directory: {output_dir}")
    if args.select_interface:
        print(f"Interface Selection: Per-frame (dynamic)")
        print(f"  - Protein cutoff: {args.interface_cutoff}Å")
        print(f"  - Water cutoff: {water_cutoff}Å")
    else:
        print(f"Interface Selection: Disabled (all atoms kept)")
    print(f"Chains: {args.chains}")
    print(f"CoCoMaps Mode: {'WITH reduce' if args.use_reduce else 'WITHOUT reduce'}")
    print(f"Water Renaming: All SOL/WAT/TIP3 → HOH (automatic)")
    print(f"{'='*80}")
    
    overall_start = time.time()
    
    try:
        step_num = 1
        
        # STEP 1: Process frames (unified function handles both modes)
        if len(args.chains) < 2:
            print("Warning: Interface selection requires 2 chains. Using A and B as defaults.")
            chain_a, chain_b = 'A', 'B'
        else:
            chain_a, chain_b = args.chains[0], args.chains[1]
        
        output_dir, frame_count, frame_stats = process_frames(
            args.pdb_file,
            output_dir,
            chain_a=chain_a,
            chain_b=chain_b,
            select_interface=args.select_interface,
            cutoff=args.interface_cutoff,
            water_cutoff=water_cutoff,
            verbose=True,
            step_num=step_num
        )
        step_num += 1

        # Fail early if interface selection produced no atoms in any frame (wrong chains)
        if args.select_interface and frame_stats and all(s.get('total_atoms', 0) == 0 for s in frame_stats):
            print("\nError: No interface atoms found in any frame.")
            print("  This usually means the chain IDs do not match the PDB.")
            print("  Example: 1ULL has chains A (RNA) and B (REV peptide); use: -c A B")
            return 1

        # STEP 2: Create input JSON files
        create_input_jsons(output_dir, frame_count, args.chains, interface_cutoff=args.interface_cutoff, use_reduce=args.use_reduce)
        
        # STEP 3: Run CoCoMaps
        analysis_time, successful, failed = run_cocomaps_analysis(
            output_dir, args.use_reduce, step_num=step_num
        )
        step_num += 1

        # STEP 4: Conserved island analysis
        from .conserved_islands import run_conserved_islands
        run_conserved_islands(
            output_dir,
            min_consistency=0.70,
            min_island_size=2,
            verbose=True,
            step_num=step_num,
        )
        step_num += 1

        # STEP 5: Aggregate per-frame CSVs into system-level files
        from .aggregate_csv import aggregate_system
        print(f"\n{'='*80}")
        print(f"STEP {step_num}: Aggregating system CSVs")
        print(f"{'='*80}")
        aggregate_system(output_dir, verbose=True)
        step_num += 1

        # Final summary
        total_time = time.time() - overall_start
        print(f"\n{'='*80}")
        print("PIPELINE COMPLETE")
        print(f"{'='*80}")
        print(f"Total pipeline time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        print(f"Results saved in: {output_dir}")
        print(f"{'='*80}\n")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        import traceback
        print(f"\n✗ Pipeline failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
