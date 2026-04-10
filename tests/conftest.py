"""Shared fixtures for the PDB-examples test suite."""
import json
import os
import shutil
import tempfile

import pytest

from backend.app import create_app


# ---------------------------------------------------------------------------
# Minimal PDB content for tests that need a valid single-frame PDB
# ---------------------------------------------------------------------------

MINIMAL_PDB = """\
MODEL        1
ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       2.000   2.000   3.000  1.00  0.00           C
ATOM      3  C   ALA A   1       3.000   2.000   3.000  1.00  0.00           C
ATOM      4  O   ALA A   1       3.500   3.000   3.000  1.00  0.00           O
ATOM      5  N   GLY B   1       1.000   2.000   6.000  1.00  0.00           N
ATOM      6  CA  GLY B   1       2.000   2.000   6.000  1.00  0.00           C
ATOM      7  C   GLY B   1       3.000   2.000   6.000  1.00  0.00           C
ATOM      8  O   GLY B   1       3.500   3.000   6.000  1.00  0.00           O
ENDMDL
END
"""

TWO_FRAME_PDB = """\
MODEL        1
ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       2.000   2.000   3.000  1.00  0.00           C
ATOM      3  N   GLY B   1       1.000   2.000   6.000  1.00  0.00           N
ATOM      4  CA  GLY B   1       2.000   2.000   6.000  1.00  0.00           C
ENDMDL
MODEL        2
ATOM      1  N   ALA A   1       1.100   2.100   3.100  1.00  0.00           N
ATOM      2  CA  ALA A   1       2.100   2.100   3.100  1.00  0.00           C
ATOM      3  N   GLY B   1       1.100   2.100   6.100  1.00  0.00           N
ATOM      4  CA  GLY B   1       2.100   2.100   6.100  1.00  0.00           C
ENDMDL
END
"""


@pytest.fixture()
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    d = tempfile.mkdtemp(prefix="pdb_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def sample_pdb(tmp_dir):
    """Write a minimal single-frame PDB file and return its path."""
    path = os.path.join(tmp_dir, "test.pdb")
    with open(path, "w") as f:
        f.write(MINIMAL_PDB)
    return path


@pytest.fixture()
def two_frame_pdb(tmp_dir):
    """Write a two-frame PDB file and return its path."""
    path = os.path.join(tmp_dir, "two_frame.pdb")
    with open(path, "w") as f:
        f.write(TWO_FRAME_PDB)
    return path


@pytest.fixture()
def fake_system(tmp_dir):
    """Create a minimal fake 'system' directory with one frame and stub CSVs.

    Returns the system directory path.
    """
    system_dir = os.path.join(tmp_dir, "systems", "test_system")
    frame_dir = os.path.join(system_dir, "frame_1")
    os.makedirs(frame_dir)

    # Stub _interactions.csv (columns must match what backend/routes/data.py expects)
    interactions_csv = os.path.join(system_dir, "_interactions.csv")
    with open(interactions_csv, "w") as f:
        f.write("frame,resName1,resNum1,chain1,resName2,resNum2,chain2,types\n")
        f.write("1,ALA,1,A,GLY,1,B,H-bond\n")

    # Stub _area.csv (columns must match what backend/routes/data.py expects)
    area_csv = os.path.join(system_dir, "_area.csv")
    with open(area_csv, "w") as f:
        f.write("frame,totalBSA,polarBSA,nonPolarBSA,totalPercent,polarPercent,nonPolarPercent\n")
        f.write("1,100.0,40.0,60.0,10.0,4.0,6.0\n")

    # Stub _trends.csv (columns must match TRENDS_KEYS in data.py)
    trends_csv = os.path.join(system_dir, "_trends.csv")
    with open(trends_csv, "w") as f:
        f.write("frame,H-bond,Salt bridge,S-S bond,Water-mediated,Metal-mediated,CH-O/N bond,Halogen bond,pi-pi,Lonepair-pi,Anion-pi,Cation-pi,Amino-pi,O/N/SH-pi,CH-pi,Polar vdW,Apolar vdW,Clash,Proximal\n")
        f.write("1,5,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n")

    # Stub _metadata.json
    meta = os.path.join(system_dir, "_metadata.json")
    with open(meta, "w") as f:
        json.dump({"displayName": "Test System", "totalFrames": 1, "chainPattern": "A_B"}, f)

    # Stub final_file CSV in frame dir (for chain pattern detection)
    final_csv = os.path.join(frame_dir, "frame_1.pdb_A_B_final_file.csv")
    with open(final_csv, "w") as f:
        f.write("Res. Name 1,Res. Number 1,Chain 1,Res. Name 2,Res. Number 2,Chain 2,Type of Interactions\n")
        f.write("ALA,1,A,GLY,1,B,H-bond\n")

    return system_dir


@pytest.fixture()
def app(fake_system):
    """Create a Flask test app whose DATA_FOLDER / UPLOAD_FOLDER point at the
    temp directory containing fake_system."""
    root = os.path.dirname(os.path.dirname(fake_system))  # tmp_dir
    application = create_app()
    application.config.update(
        TESTING=True,
        UPLOAD_FOLDER=root,
        DATA_FOLDER=root,
    )
    return application


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()
