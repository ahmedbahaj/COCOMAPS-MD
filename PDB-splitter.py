from MDAnalysis.coordinates import PDB
import MDAnalysis as mda
import os
from pathlib import Path

#constants
PDB_FILE = "systems/5ak0_JB00_st0_c2_prod_50f_full.pdb"  # Change this to your PDB file path

u = mda.Universe(PDB_FILE)

pdb_name = Path(PDB_FILE).stem
# Keep output in systems directory
if PDB_FILE.startswith("systems/"):
    main_folder = os.path.join("systems", pdb_name)
else:
    main_folder = pdb_name

#create main folder for the pdb file
os.makedirs(main_folder, exist_ok=True)

# Copy original PDB file into output folder
import shutil
original_pdb = Path(PDB_FILE).name
if not os.path.exists(os.path.join(main_folder, original_pdb)):
    shutil.copy(PDB_FILE, os.path.join(main_folder, original_pdb))

#iterate through frames
for i, ts in enumerate(u.trajectory):
    frame_folder = os.path.join(main_folder, f"frame_{i+1}")
    os.makedirs(frame_folder, exist_ok=True)

    frame_file = os.path.join(frame_folder, f"frame_{i+1}.pdb")
    with PDB.PDBWriter(frame_file) as W:
        W.write(u.atoms)
