"""Tests for engine.conserved_islands — file discovery handles both
reduce (pd_h.pdb) and no-reduce (pdb) naming conventions.
"""
import os

import pytest

from engine.conserved_islands import _find_final_files
from pathlib import Path


@pytest.fixture()
def system_with_no_reduce(tmp_dir):
    """System where CoCoMaps ran without reduce (standard .pdb naming)."""
    frame = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame)
    csv_path = os.path.join(frame, "frame_1.pdb_A_B_final_file.csv")
    with open(csv_path, "w") as f:
        f.write("Res. Name 1,Res. Number 1,Chain 1,Res. Name 2,Res. Number 2,Chain 2,Type of Interactions\n")
        f.write("ALA,1,A,GLY,1,B,H-bond\n")
    return tmp_dir


@pytest.fixture()
def system_with_reduce(tmp_dir):
    """System where CoCoMaps ran with reduce (pd_h.pdb naming)."""
    frame = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame)
    csv_path = os.path.join(frame, "frame_1.pd_h.pdb_A_B_final_file.csv")
    with open(csv_path, "w") as f:
        f.write("Res. Name 1,Res. Number 1,Chain 1,Res. Name 2,Res. Number 2,Chain 2,Type of Interactions\n")
        f.write("ALA,1,A,GLY,1,B,H-bond\n")
    return tmp_dir


class TestFindFinalFiles:
    def test_finds_no_reduce_naming(self, system_with_no_reduce):
        files = _find_final_files(Path(system_with_no_reduce))
        assert len(files) == 1
        assert "frame_1.pdb_A_B_final_file.csv" in files[0].name

    def test_finds_reduce_naming(self, system_with_reduce):
        files = _find_final_files(Path(system_with_reduce))
        assert len(files) == 1
        assert "pd_h.pdb" in files[0].name

    def test_empty_dir_returns_empty(self, tmp_dir):
        os.makedirs(os.path.join(tmp_dir, "frame_1"))
        files = _find_final_files(Path(tmp_dir))
        assert files == []
