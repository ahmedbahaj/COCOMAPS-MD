#!/usr/bin/env python3
"""
Complete PDB Analysis Pipeline
1. (Optional) Per-frame interface selection + splitting (or just splitting)
2. Run CoCoMaps analysis on each frame

When interface selection is enabled:
- Each frame keeps ONLY residues at the interface IN THAT SPECIFIC FRAME
- Atom counts may vary between frames (dynamic interface)
- This is more optimized than keeping all interface residues across all frames
"""

import subprocess
import os
import time
import argparse
import json
import shutil
from pathlib import Path
from distutils.util import strtobool
import MDAnalysis as mda
from MDAnalysis.coordinates import PDB
from dotenv import load_dotenv

# Load .env file from the same directory as this script
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Import from interface_selector
from interface_selector import select_interface_per_frame

# Docker configuration (loaded from .env or defaults)
DOCKER_IMAGE_REDUCE = os.environ.get("COCOMAPS_IMAGE_REDUCE", "andrpet/cocomaps-backend:0.0.19")
DOCKER_IMAGE_NO_REDUCE = os.environ.get(
    "COCOMAPS_IMAGE_NO_REDUCE", "sattamaltwaim/cocomaps-backend:no-reduce"
)
USE_REDUCE = bool(strtobool(os.environ.get("COCOMAPS_USE_REDUCE", "false")))
INPUT_FILE_NAME = os.environ.get("INPUT_FILE_NAME", "example_input.json")

# Default parameters (loaded from .env or defaults)
DEFAULT_INTERFACE_CUTOFF = float(os.environ.get("DEFAULT_INTERFACE_CUTOFF", "5.0"))
SELECT_INTERFACE = bool(strtobool(os.environ.get("SELECT_INTERFACE", "false")))
_chains_env = os.environ.get("DEFAULT_CHAINS", "A,B")
DEFAULT_CHAINS = [c.strip() for c in _chains_env.split(',')]


def split_pdb(pdb_file, output_dir, copy_original=True, step_num=None):
    """Split PDB file into individual frames"""
    step_label = f"STEP {step_num}: " if step_num else ""
    print(f"\n{'='*80}")
    print(f"{step_label}Splitting PDB into frames")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    u = mda.Universe(pdb_file)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy original PDB to output directory
    if copy_original:
        original_name = Path(pdb_file).name
        dest_path = os.path.join(output_dir, original_name)
        if not os.path.exists(dest_path):
            shutil.copy(pdb_file, dest_path)
            print(f"Copied original PDB to: {dest_path}")
    
    # Split into frames
    frame_count = 0
    for i, ts in enumerate(u.trajectory):
        frame_folder = os.path.join(output_dir, f"frame_{i+1}")
        os.makedirs(frame_folder, exist_ok=True)
        
        frame_file = os.path.join(frame_folder, f"frame_{i+1}.pdb")
        with PDB.PDBWriter(frame_file) as W:
            W.write(u.atoms)
        frame_count += 1
    
    elapsed = time.time() - start_time
    print(f"✓ Split {frame_count} frames in {elapsed:.2f} seconds")
    print(f"  Output directory: {output_dir}")
    
    return output_dir, frame_count


def create_input_jsons(output_dir, frame_count, chains=None):
    """Create example_input.json files for each frame"""
    if chains is None:
        chains = DEFAULT_CHAINS
    
    print(f"\nCreating input JSON files for {frame_count} frames...")
    
    for i in range(1, frame_count + 1):
        frame_folder = os.path.join(output_dir, f"frame_{i}")
        json_file = os.path.join(frame_folder, INPUT_FILE_NAME)
        
        json_data = {
            "pdb_file": f"/app/data/frame_{i}.pdb",
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
            "CUT_OFF": 5,
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


def run_cocomaps_analysis(output_dir, use_reduce=False, step_num=None):
    """Run CoCoMaps Docker analysis on all frames"""
    step_label = f"STEP {step_num}: " if step_num else ""
    print(f"\n{'='*80}")
    print(f"{step_label}Running CoCoMaps Analysis ({'WITH' if use_reduce else 'WITHOUT'} reduce)")
    print(f"{'='*80}")
    
    docker_image = DOCKER_IMAGE_REDUCE if use_reduce else DOCKER_IMAGE_NO_REDUCE
    print(f"Docker Image: {docker_image}\n")
    
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
    print(f"Found {len(frame_numbers)} frames to process\n")
    
    start_time = time.time()
    successful = 0
    failed = 0
    
    for i in frame_numbers:
        frame_folder = f"frame_{i}"
        frame_path = os.path.join(output_dir, frame_folder)
        
        container_input_path = f"/app/data/{INPUT_FILE_NAME}"
        docker_command = (
            f'docker run '
            f'-v "{os.path.abspath(frame_path)}":/app/data '
            f'{docker_image} '
            f'python /app/coco2/begin.py {container_input_path}'
        )
        
        print(f"Processing frame {i}...", end=" ", flush=True)
        
        try:
            subprocess.run(
                docker_command, shell=True, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            print("✓")
            successful += 1
        except subprocess.CalledProcessError as e:
            print("✗")
            print(f"  Error: {e.output[:200]}")
            failed += 1
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print("CoCoMaps Analysis Complete")
    print(f"{'='*80}")
    print(f"Successful: {successful}/{len(frame_numbers)}")
    print(f"Failed: {failed}/{len(frame_numbers)}")
    print(f"Total time: {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Average time per frame: {elapsed/len(frame_numbers):.2f} seconds")
    
    return elapsed, successful, failed


def main():
    parser = argparse.ArgumentParser(
        description="Complete PDB analysis pipeline with interface selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (interface selection OFF by default)
  python analyze_pdb.py systems/my_protein.pdb
  
  # Enable per-frame interface selection
  # (each frame keeps only residues at interface in THAT frame)
  python analyze_pdb.py systems/my_protein.pdb --interface
  
  # Interface selection with custom cutoff (default: 5Å)
  python analyze_pdb.py systems/my_protein.pdb --interface --interface-cutoff 7.0
  
  # Separate cutoffs for protein interface and water bridges
  python analyze_pdb.py systems/my_protein.pdb --interface --interface-cutoff 5.0 --water-cutoff 3.5
  
  # Enable reduce (adds hydrogens, slower)
  python analyze_pdb.py systems/my_protein.pdb --use-reduce
  
  # Custom output directory
  python analyze_pdb.py systems/my_protein.pdb -o systems/my_output

Interface Selection Mode:
  When --interface is enabled, each frame is processed independently:
  - Only residues within cutoff distance of the partner chain IN THAT FRAME are kept
  - Atom counts may vary between frames (dynamic interface)
  - Bridging waters (within cutoff of BOTH chains) are also kept per-frame

Environment Variables:
  SELECT_INTERFACE=true/false    - Enable/disable interface selection (default: false)
  COCOMAPS_USE_REDUCE=true/false - Enable/disable reduce (default: false)
  COCOMAPS_IMAGE_REDUCE          - Docker image for reduce mode
  COCOMAPS_IMAGE_NO_REDUCE       - Docker image for no-reduce mode
  DEFAULT_INTERFACE_CUTOFF       - Interface/water cutoff in Angstroms (default: 5.0)
        """
    )
    
    parser.add_argument('pdb_file', help='Input PDB file to analyze')
    parser.add_argument('-o', '--output', help='Output directory (default: systems/<pdb_name>)')
    parser.add_argument('--use-reduce', dest='use_reduce', action='store_true',
                       help='Use reduce version of CoCoMaps (can also set COCOMAPS_USE_REDUCE=true)')
    parser.add_argument('--no-reduce', dest='use_reduce', action='store_false',
                       help='Use no-reduce version of CoCoMaps (can also set COCOMAPS_USE_REDUCE=false)')
    parser.add_argument('-c', '--chains', nargs='+', default=DEFAULT_CHAINS,
                       help='Chain IDs to analyze (default: A B)')
    
    # Interface selection options
    parser.add_argument('--interface', dest='select_interface', action='store_true',
                       help='Enable per-frame interface selection - each frame keeps only its own interface residues')
    parser.add_argument('--no-interface', dest='select_interface', action='store_false',
                       help='Disable interface selection (keep all atoms)')
    parser.add_argument('--interface-cutoff', type=float, default=DEFAULT_INTERFACE_CUTOFF,
                       help=f'Interface selection cutoff in Angstroms (default: {DEFAULT_INTERFACE_CUTOFF})')
    parser.add_argument('--water-cutoff', type=float, default=None,
                       help=f'Bridging water cutoff in Angstroms (default: same as interface-cutoff)')
    
    # Set defaults from environment variables
    parser.set_defaults(use_reduce=USE_REDUCE, select_interface=SELECT_INTERFACE)
    
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
        print(f"  - Each frame keeps only its own interface residues")
    else:
        print(f"Interface Selection: Disabled (all atoms kept)")
    print(f"Chains: {args.chains}")
    print(f"CoCoMaps Mode: {'WITH reduce' if args.use_reduce else 'WITHOUT reduce'}")
    print(f"{'='*80}")
    
    overall_start = time.time()
    
    try:
        step_num = 1
        
        # STEP 1: Interface selection + splitting OR just splitting
        if args.select_interface:
            # Per-frame interface selection (combines interface selection and splitting)
            print(f"\n{'='*80}")
            print(f"STEP {step_num}: Per-frame interface selection + splitting")
            print(f"{'='*80}")
            print("Mode: Each frame keeps only residues at interface IN THAT FRAME")
            print("      (atom counts may vary between frames)\n")
            
            # Need exactly 2 chains for interface selection
            if len(args.chains) < 2:
                print("Warning: Interface selection requires 2 chains. Using A and B as defaults.")
                chain_a, chain_b = 'A', 'B'
            else:
                chain_a, chain_b = args.chains[0], args.chains[1]
            
            # This function does both interface selection AND frame splitting
            output_dir, frame_count = select_interface_per_frame(
                args.pdb_file,
                output_dir=output_dir,
                chain_a=chain_a,
                chain_b=chain_b,
                cutoff=args.interface_cutoff,
                water_cutoff=water_cutoff,
                verbose=True
            )
            step_num += 1
        else:
            # No interface selection - just split the PDB
            output_dir, frame_count = split_pdb(args.pdb_file, output_dir, copy_original=True, step_num=step_num)
            step_num += 1
        
        # Create input JSON files
        create_input_jsons(output_dir, frame_count, args.chains)
        
        # STEP: Run CoCoMaps
        analysis_time, successful, failed = run_cocomaps_analysis(output_dir, args.use_reduce, step_num=step_num)
        
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
