"""Tests for engine.analyze_pdb.run_cocomaps_analysis — verify it
constructs the correct local subprocess command (no Docker) and
correctly counts successes / failures.
"""
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from engine.analyze_pdb import run_cocomaps_analysis, COCOMAPS_DIR, INPUT_FILE_NAME


@pytest.fixture()
def cocomaps_frame_dir(tmp_dir):
    """Create a one-frame output dir with a stub input JSON."""
    frame_dir = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame_dir)
    json_path = os.path.join(frame_dir, INPUT_FILE_NAME)
    with open(json_path, "w") as f:
        json.dump({"pdb_file": "frame_1.pdb", "REDUCE_BOOL": False}, f)
    return tmp_dir


class TestRunCocomapsAnalysis:
    @patch("engine.analyze_pdb.subprocess.run")
    def test_calls_local_subprocess_not_docker(self, mock_run, cocomaps_frame_dir):
        mock_run.return_value = MagicMock(returncode=0)
        _, successful, failed = run_cocomaps_analysis(cocomaps_frame_dir, use_reduce=False)

        assert successful == 1
        assert failed == 0
        call_args = mock_run.call_args
        command = call_args[0][0]
        assert command[0] == sys.executable
        assert "begin.py" in command[1]
        assert "docker" not in " ".join(command).lower()

    @patch("engine.analyze_pdb.subprocess.run")
    def test_cocomaps_dir_path(self, mock_run, cocomaps_frame_dir):
        mock_run.return_value = MagicMock(returncode=0)
        run_cocomaps_analysis(cocomaps_frame_dir, use_reduce=False)

        call_args = mock_run.call_args
        begin_script = call_args[0][0][1]
        assert begin_script == str(COCOMAPS_DIR / "begin.py")

    @patch("engine.analyze_pdb.subprocess.run")
    def test_failed_frame_counted(self, mock_run, cocomaps_frame_dir):
        import subprocess as sp
        mock_run.side_effect = sp.CalledProcessError(1, "cmd", output="error")
        _, successful, failed = run_cocomaps_analysis(cocomaps_frame_dir, use_reduce=False)
        assert successful == 0
        assert failed == 1

    @patch("engine.analyze_pdb.subprocess.run")
    def test_cwd_set_to_frame_path(self, mock_run, cocomaps_frame_dir):
        mock_run.return_value = MagicMock(returncode=0)
        run_cocomaps_analysis(cocomaps_frame_dir, use_reduce=False)
        call_kwargs = mock_run.call_args[1]
        assert "cwd" in call_kwargs
        assert call_kwargs["cwd"].endswith("frame_1")

    @patch("engine.analyze_pdb.subprocess.run")
    def test_progress_callback_called(self, mock_run, cocomaps_frame_dir):
        mock_run.return_value = MagicMock(returncode=0)
        cb = MagicMock()
        run_cocomaps_analysis(cocomaps_frame_dir, use_reduce=False, progress_callback=cb)
        assert cb.called
