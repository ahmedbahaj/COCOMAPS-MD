"""Tests for the systems API routes."""
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

    def test_traversal_system_id_404(self, client):
        resp = client.get("/api/systems/%2e%2e")
        assert resp.status_code == 404


class TestRenameDisabled:
    def test_rename_endpoint_is_not_exposed(self, client, fake_system):
        resp = client.post(
            "/api/systems/test_system/rename",
            json={"name": "Renamed System"},
        )
        assert resp.status_code == 404

        meta_path = os.path.join(fake_system, ".metadata.json")
        assert not os.path.exists(meta_path)

    def test_traversal_rename_is_not_exposed(self, client, fake_system):
        root = os.path.dirname(os.path.dirname(fake_system))
        escaped_meta = os.path.join(root, ".metadata.json")

        resp = client.post(
            "/api/systems/%2e%2e/rename",
            json={"name": "Escaped"},
        )

        assert resp.status_code == 404
        assert not os.path.exists(escaped_meta)
