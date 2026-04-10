"""Tests for engine.analyze_pdb.create_input_jsons — verifies that the
generated JSON files contain the correct REDUCE_BOOL flag and local
pdb_file paths (no Docker /app/data/ prefix).
"""
import json
import os

import pytest

from engine.analyze_pdb import create_input_jsons


@pytest.fixture()
def frame_dirs(tmp_dir):
    """Create two empty frame directories and return the parent dir."""
    for i in (1, 2):
        os.makedirs(os.path.join(tmp_dir, f"frame_{i}"))
    return tmp_dir


class TestCreateInputJsons:
    def test_reduce_true_written_to_json(self, frame_dirs):
        create_input_jsons(frame_dirs, frame_count=2, chains=["A", "B"], use_reduce=True)
        with open(os.path.join(frame_dirs, "frame_1", "example_input.json")) as f:
            data = json.load(f)
        assert data["REDUCE_BOOL"] is True

    def test_reduce_false_written_to_json(self, frame_dirs):
        create_input_jsons(frame_dirs, frame_count=2, chains=["A", "B"], use_reduce=False)
        with open(os.path.join(frame_dirs, "frame_1", "example_input.json")) as f:
            data = json.load(f)
        assert data["REDUCE_BOOL"] is False

    def test_pdb_path_is_local_absolute(self, frame_dirs):
        create_input_jsons(frame_dirs, frame_count=1, chains=["A", "B"], use_reduce=False)
        with open(os.path.join(frame_dirs, "frame_1", "example_input.json")) as f:
            data = json.load(f)
        pdb_path = data["pdb_file"]
        assert not pdb_path.startswith("/app/data"), "pdb_file should be a local path, not a Docker path"
        assert os.path.isabs(pdb_path)
        assert pdb_path.endswith("frame_1.pdb")

    def test_all_threshold_params_present(self, frame_dirs):
        create_input_jsons(frame_dirs, frame_count=1, chains=["X", "Y"], use_reduce=False)
        with open(os.path.join(frame_dirs, "frame_1", "example_input.json")) as f:
            data = json.load(f)
        expected_keys = [
            "HBOND_DIST", "HBOND_ANGLE", "SBRIDGE_DIST", "WBRIDGE_DIST",
            "CH_ON_DIST", "CH_ON_ANGLE", "CUT_OFF",
            "PI_PI_DIST", "PI_PI_THETA", "PI_PI_GAMMA",
            "METAL_DIST", "HALOGEN_THETA1", "HALOGEN_THETA2",
        ]
        for key in expected_keys:
            assert key in data, f"Missing expected key: {key}"

    def test_chains_written_correctly(self, frame_dirs):
        create_input_jsons(frame_dirs, frame_count=1, chains=["X", "Y"], use_reduce=False)
        with open(os.path.join(frame_dirs, "frame_1", "example_input.json")) as f:
            data = json.load(f)
        assert data["chains_set_1"] == ["X"]
        assert data["chains_set_2"] == ["Y"]

    def test_creates_correct_number_of_files(self, frame_dirs):
        create_input_jsons(frame_dirs, frame_count=2, chains=["A", "B"], use_reduce=False)
        for i in (1, 2):
            path = os.path.join(frame_dirs, f"frame_{i}", "example_input.json")
            assert os.path.isfile(path)
