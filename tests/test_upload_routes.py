"""Tests for the upload / jobs API routes."""
import io
import json
from unittest.mock import patch

import pytest


def _make_pdb_file(content=b"ATOM      1  N   ALA A   1       1.0   2.0   3.0  1.00  0.00           N\nEND\n"):
    """Return a tuple (data, filename) suitable for ``client.post(data=...)``."""
    return (io.BytesIO(content), "test.pdb")


class TestUploadRoute:
    def test_missing_file_returns_400(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_empty_file_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b""), "empty.pdb")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "empty" in data["error"].lower() or "error" in data

    def test_invalid_extension_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"hello"), "test.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    @patch("backend.routes.upload.process_pdb_async")
    def test_upload_with_reduce_true(self, mock_process, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": _make_pdb_file(),
                "reduce": "true",
                "chain1": "A",
                "chain2": "B",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "job_id" in data

        # Verify that the background thread was started with use_reduce=True
        call_args = mock_process.call_args
        assert call_args is not None
        # use_reduce is passed as positional arg [5] (app, job_id, filepath, pdb_name, system_dir, use_reduce, ...)
        assert call_args[0][5] is True

    @patch("backend.routes.upload.process_pdb_async")
    def test_upload_with_reduce_false(self, mock_process, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": _make_pdb_file(),
                "reduce": "false",
                "chain1": "A",
                "chain2": "B",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        call_args = mock_process.call_args
        assert call_args is not None
        assert call_args[0][5] is False

    @patch("backend.routes.upload.process_pdb_async")
    def test_upload_reduce_default_is_false(self, mock_process, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": _make_pdb_file(),
                "chain1": "A",
                "chain2": "B",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        call_args = mock_process.call_args
        assert call_args[0][5] is False


class TestStatusRoute:
    def test_unknown_job_returns_404(self, client):
        resp = client.get("/api/status/nonexistent-id")
        assert resp.status_code == 404


class TestJobsRoute:
    def test_list_jobs_returns_list(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
