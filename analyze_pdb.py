#!/usr/bin/env python3
"""
Complete PDB Analysis Pipeline
1. (Optional) Truncate water molecules
2. Split PDB into frames
3. Run CoCoMaps analysis on each frame
"""

import subprocess
import os
import sys
import time
import argparse
from pathlib import Path
from distutils.util import strtobool
import MDAnalysis as mda
from MDAnalysis.coordinates import PDB
from dotenv import load_dotenv

# Load .env file from the same directory as this script
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Import from truncate_waters
from truncate_waters import truncate_waters

# Docker configuration (loaded from .env or defaults)
DOCKER_IMAGE_REDUCE = os.environ.get("COCOMAPS_IMAGE_REDUCE", "andrpet/cocomaps-backend:0.0.19")
DOCKER_IMAGE_NO_REDUCE = os.environ.get(
    "COCOMAPS_IMAGE_NO_REDUCE", "sattamaltwaim/cocomaps-backend:no-reduce"
)
USE_REDUCE = bool(strtobool(os.environ.get("COCOMAPS_USE_REDUCE", "false")))
TRUNCATE_WATERS = bool(strtobool(os.environ.get("TRUNCATE_WATERS", "false")))
INPUT_FILE_NAME = os.environ.get("INPUT_FILE_NAME", "example_input.json")

# Default parameters (loaded from .env or defaults)
DEFAULT_WATER_DISTANCE = float(os.environ.get("DEFAULT_WATER_DISTANCE", "5.0"))
_chains_env = os.environ.get("DEFAULT_CHAINS", "A,B")
DEFAULT_CHAINS = [c.strip() for c in _chains_env.split(',')]


def split_pdb(pdb_file, output_dir, copy_original=True):
    """Split PDB file into individual frames"""
    print(f"\n{'='*80}")
    print("STEP 2: Splitting PDB into frames")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    u = mda.Universe(pdb_file)
    pdb_name = Path(pdb_file).stem
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy original PDB to output directory
    if copy_original:
        import shutil
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
    
    import json
    
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


def run_cocomaps_analysis(output_dir, use_reduce=False):
    """Run CoCoMaps Docker analysis on all frames"""
    print(f"\n{'='*80}")
    print(f"STEP 3: Running CoCoMaps Analysis ({'WITH' if use_reduce else 'WITHOUT'} reduce)")
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
            f'{container_input_path}'
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
        description="Complete PDB analysis pipeline with water truncation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (water truncation ON by default, reduce OFF by default)
  python analyze_pdb.py systems/my_protein.pdb
  
  # Disable water truncation
  python analyze_pdb.py systems/my_protein.pdb --no-truncate
  
  # Enable reduce (adds hydrogens, slower)
  python analyze_pdb.py systems/my_protein.pdb --use-reduce
  
  # Custom water distance threshold (7Å instead of default 5Å)
  python analyze_pdb.py systems/my_protein.pdb -d 7.0
  
  # Use environment variables
  TRUNCATE_WATERS=false COCOMAPS_USE_REDUCE=true python analyze_pdb.py systems/my_protein.pdb
  
  # Custom output directory
  python analyze_pdb.py systems/my_protein.pdb -o systems/my_output

Environment Variables:
  TRUNCATE_WATERS=true/false     - Enable/disable water truncation (default: true)
  COCOMAPS_USE_REDUCE=true/false - Enable/disable reduce (default: false)
  COCOMAPS_IMAGE_REDUCE          - Docker image for reduce mode
  COCOMAPS_IMAGE_NO_REDUCE       - Docker image for no-reduce mode
        """
    )
    
    parser.add_argument('pdb_file', help='Input PDB file to analyze')
    parser.add_argument('-o', '--output', help='Output directory (default: systems/<pdb_name>)')
    parser.add_argument('-d', '--water-distance', type=float, default=DEFAULT_WATER_DISTANCE,
                       help=f'Water truncation distance in Angstroms (default: {DEFAULT_WATER_DISTANCE})')
    parser.add_argument('--truncate', dest='truncate_waters', action='store_true',
                       help='Enable water truncation (can also set TRUNCATE_WATERS=true)')
    parser.add_argument('--no-truncate', dest='truncate_waters', action='store_false',
                       help='Disable water truncation (can also set TRUNCATE_WATERS=false)')
    parser.add_argument('--use-reduce', dest='use_reduce', action='store_true',
                       help='Use reduce version of CoCoMaps (can also set COCOMAPS_USE_REDUCE=true)')
    parser.add_argument('--no-reduce', dest='use_reduce', action='store_false',
                       help='Use no-reduce version of CoCoMaps (can also set COCOMAPS_USE_REDUCE=false)')
    parser.add_argument('-c', '--chains', nargs='+', default=DEFAULT_CHAINS,
                       help='Chain IDs to analyze (default: A B)')
    
    # Set defaults from environment variables
    parser.set_defaults(truncate_waters=TRUNCATE_WATERS, use_reduce=USE_REDUCE)
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.pdb_file):
        print(f"Error: PDB file not found: {args.pdb_file}")
        return 1
    
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
    print(f"Water Truncation: {'Yes' if args.truncate_waters else 'No'} " +
          (f"({args.water_distance}Å)" if args.truncate_waters else ""))
    print(f"Chains: {args.chains}")
    print(f"CoCoMaps Mode: {'WITH reduce' if args.use_reduce else 'WITHOUT reduce'}")
    print(f"{'='*80}")
    
    overall_start = time.time()
    
    try:
        # STEP 1: Truncate waters (optional)
        pdb_to_split = args.pdb_file
        if args.truncate_waters:
            print(f"\n{'='*80}")
            print("STEP 1: Truncating water molecules")
            print(f"{'='*80}")
            
            truncated_pdb = truncate_waters(
                args.pdb_file,
                output_pdb=None,  # Will auto-generate name
                distance=args.water_distance,
                chains=args.chains,
                verbose=True
            )
            pdb_to_split = truncated_pdb
        else:
            print(f"\n{'='*80}")
            print("STEP 1: Skipped (water truncation disabled)")
            print(f"{'='*80}")
        
        # STEP 2: Split PDB
        output_dir, frame_count = split_pdb(pdb_to_split, output_dir, copy_original=True)
        
        # Create input JSON files
        create_input_jsons(output_dir, frame_count, args.chains)
        
        # STEP 3: Run CoCoMaps
        analysis_time, successful, failed = run_cocomaps_analysis(output_dir, args.use_reduce)
        
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
        print(f"\n✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

