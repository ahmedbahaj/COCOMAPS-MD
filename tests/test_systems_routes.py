"""Tests for the systems API routes."""
import json
import os

import pytest


class TestListSystems:
    def test_returns_list(self, client):
        resp = client.get("/api/systems")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_fake_system_appears(self, client):
        resp = client.get("/api/systems")
        data = resp.get_json()
        ids = [s["id"] for s in data]
        assert "test_system" in ids

    def test_system_has_expected_fields(self, client):
        resp = client.get("/api/systems")
        data = resp.get_json()
        system = next(s for s in data if s["id"] == "test_system")
        assert "name" in system
        assert "frames" in system


class TestSystemDetail:
    def test_known_system(self, client):
        resp = client.get("/api/systems/test_system")
        assert resp.status_code == 200

    def test_unknown_system_404(self, client):
        resp = client.get("/api/systems/no_such_system")
        assert resp.status_code == 404


class TestRename:
    def test_rename_system(self, client, fake_system):
        resp = client.post(
            "/api/systems/test_system/rename",
            json={"name": "Renamed System"},
        )
        assert resp.status_code == 200

        # _set_display_name writes to .metadata.json (dot prefix)
        meta_path = os.path.join(fake_system, ".metadata.json")
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta.get("displayName") == "Renamed System"
