"""Tests for engine.aggregate_csv — verify aggregation handles both
reduce (pd_h.pdb) and no-reduce file naming.
"""
import csv
import os

import pytest

from engine.aggregate_csv import aggregate_system


def _write_cocomaps_frame(frame_dir, frame_num, chain_pattern="A_B", use_reduce=False):
    """Write minimal stub CSVs that aggregate_system expects per frame."""
    stem = f"frame_{frame_num}.pd_h.pdb" if use_reduce else f"frame_{frame_num}.pdb"

    # final_file.csv
    final = os.path.join(frame_dir, f"{stem}_{chain_pattern}_final_file.csv")
    with open(final, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Res. Name 1", "Res. Number 1", "Chain 1",
                     "Res. Name 2", "Res. Number 2", "Chain 2",
                     "Type of Interactions"])
        w.writerow(["ALA", "1", "A", "GLY", "1", "B", "H-bond"])

    # Rsa_stats.csv
    rsa = os.path.join(frame_dir, f"{stem}_{chain_pattern}_complex.pdb_Rsa_stats.csv")
    with open(rsa, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Property", "Value"])
        w.writerow(["Buried area upon the complex formation / Interface area (Å²)", "100.0"])
        w.writerow(["Buried area upon the complex formation (%)", "10.0"])
        w.writerow(["POLAR Buried area upon the complex formation / Interface area (Å²)", "40.0"])
        w.writerow(["POLAR Interface (%)", "4.0"])
        w.writerow(["NON POLAR Buried area upon the complex formation / Interface area (Å²)", "60.0"])
        w.writerow(["NON POLAR Interface (%)", "6.0"])

    # summary_table.csv
    summary = os.path.join(frame_dir, f"{stem}_{chain_pattern}_summary_table.csv")
    with open(summary, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Property", "Value"])
        w.writerow(["Number of H-bonds", "5"])


@pytest.fixture()
def system_no_reduce(tmp_dir):
    frame_dir = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame_dir)
    _write_cocomaps_frame(frame_dir, 1, use_reduce=False)
    return tmp_dir


@pytest.fixture()
def system_reduce(tmp_dir):
    frame_dir = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame_dir)
    _write_cocomaps_frame(frame_dir, 1, use_reduce=True)
    return tmp_dir


class TestAggregateCSV:
    def test_aggregation_no_reduce(self, system_no_reduce):
        aggregate_system(system_no_reduce, verbose=False)
        assert os.path.isfile(os.path.join(system_no_reduce, "_interactions.csv"))
        assert os.path.isfile(os.path.join(system_no_reduce, "_metadata.json"))

    def test_aggregation_reduce(self, system_reduce):
        aggregate_system(system_reduce, verbose=False)
        assert os.path.isfile(os.path.join(system_reduce, "_interactions.csv"))
        assert os.path.isfile(os.path.join(system_reduce, "_metadata.json"))
