"""Tests for the data retrieval API routes."""
import pytest


class TestInteractions:
    def test_returns_data(self, client):
        resp = client.get("/api/systems/test_system/interactions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))

    def test_unknown_system_404(self, client):
        resp = client.get("/api/systems/nonexistent/interactions")
        assert resp.status_code == 404


class TestArea:
    def test_returns_data(self, client):
        resp = client.get("/api/systems/test_system/area")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))


class TestTrends:
    def test_returns_data(self, client):
        resp = client.get("/api/systems/test_system/trends")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))


class TestConservedIslands:
    def test_missing_file_returns_empty(self, client):
        resp = client.get("/api/systems/test_system/conserved-islands")
        # Should return 200 with empty or error gracefully
        assert resp.status_code in (200, 404)
