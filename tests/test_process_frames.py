"""Tests for engine.analyze_pdb.process_frames — frame splitting, water
renaming, and frame range/step logic.
"""
import os

import pytest

from engine.analyze_pdb import process_frames, rename_waters_to_hoh


class TestProcessFrames:
    def test_single_frame_split(self, sample_pdb, tmp_dir):
        out_dir = os.path.join(tmp_dir, "output")
        _, count, stats = process_frames(
            sample_pdb, out_dir, chain_a="A", chain_b="B",
            select_interface=False, verbose=False,
        )
        assert count == 1
        frame_pdb = os.path.join(out_dir, "frame_1", "frame_1.pdb")
        assert os.path.isfile(frame_pdb)

    def test_two_frame_split(self, two_frame_pdb, tmp_dir):
        out_dir = os.path.join(tmp_dir, "output")
        _, count, stats = process_frames(
            two_frame_pdb, out_dir, chain_a="A", chain_b="B",
            select_interface=False, verbose=False,
        )
        assert count == 2
        for i in (1, 2):
            assert os.path.isfile(os.path.join(out_dir, f"frame_{i}", f"frame_{i}.pdb"))

    def test_frame_step(self, two_frame_pdb, tmp_dir):
        out_dir = os.path.join(tmp_dir, "output")
        _, count, _ = process_frames(
            two_frame_pdb, out_dir, chain_a="A", chain_b="B",
            select_interface=False, verbose=False, frame_step=2,
        )
        assert count == 1

    def test_start_end_frame(self, two_frame_pdb, tmp_dir):
        out_dir = os.path.join(tmp_dir, "output")
        _, count, _ = process_frames(
            two_frame_pdb, out_dir, chain_a="A", chain_b="B",
            select_interface=False, verbose=False,
            start_frame=1, end_frame=2,
        )
        assert count == 1

    def test_stats_populated(self, sample_pdb, tmp_dir):
        out_dir = os.path.join(tmp_dir, "output")
        _, _, stats = process_frames(
            sample_pdb, out_dir, chain_a="A", chain_b="B",
            select_interface=False, verbose=False,
        )
        assert len(stats) == 1
        assert stats[0]["total_atoms"] > 0
        assert stats[0]["frame"] == 1


class TestRenameWaters:
    def test_sol_renamed_to_hoh(self, tmp_dir):
        """SOL residues should be renamed to HOH."""
        import MDAnalysis as mda

        pdb_content = """\
ATOM      1  OW  SOL A   1       1.000   2.000   3.000  1.00  0.00           O
END
"""
        pdb_path = os.path.join(tmp_dir, "water.pdb")
        with open(pdb_path, "w") as f:
            f.write(pdb_content)
        u = mda.Universe(pdb_path)
        rename_waters_to_hoh(u.atoms)
        assert u.residues[0].resname == "HOH"
