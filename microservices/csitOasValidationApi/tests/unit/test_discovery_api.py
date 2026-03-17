"""
API-level unit tests for the Discovery endpoints
Tests how the service responds via HTTP under various conditions.
No direct instantiation of DiscoveryApiImpl — all via TestClient.
"""

import pytest
import respx
from pathlib import Path
from fastapi.testclient import TestClient
from csit_validation.core.config import get_github_tag_cache_path
from urllib.parse import quote

def urlquote(s: str) -> str:
    """Encode everything, including / → %2F (no safe characters)"""
    return quote(s, safe='')

class TestDiscoveryApi:

    # ── Successful version list → 200 OK with sorted versions ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")  # ← if you want logs
    def test_list_versions_success_200(self, client: TestClient, caplog, monkeypatch):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        response = client.get("/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert data["versions"] == ["v1.3.0-beta1","v1.3.0-Beta1","v1.2.3","v1.1.0","v1.0.0"]  # sorted newest first

        assert "200" in caplog.text

    # ── Empty version list → 200 OK with empty array ───────────────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_list_versions_empty_success_200(self, client: TestClient, caplog, monkeypatch):

        cache_dir = Path(__file__).parent / "resources" / "github-cache-empty"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        response = client.get("/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert data["versions"] == []  # empty

        assert "200" in caplog.text

    # Version (tag) not found → 404 Not Found
    @respx.mock
    def test_list_rulesets_version_not_found_404(self, client: TestClient, monkeypatch):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        version = "v1.3.0" # Does not have the prefix

        response = client.get(f"/versions/{version}/rulesets")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Version '{version}' not found" in data["detail"]

    # Successful ruleset list → 200 OK with sorted rulesets
    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_list_rulesets_success_200(self, client: TestClient, caplog, monkeypatch):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        version = "v1.1.0"

        response = client.get(f"/versions/{urlquote(version)}/rulesets")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == version
        assert "rulesets" in data
        assert data["rulesets"] == [
            "basic-ruleset",
            "strict-ruleset",
            "internal/private/ruleset-a",
            "internal/private/ruleset-b",
            "internal/shared/ruleset-a",
            "internal/shared/ruleset-b",
            "sdx/ruleset"
        ]  # sorted alphabetically

        assert "200" in caplog.text

    # Successful ruleset list → 200 OK with no rulesets
    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_list_rulesets_empty_success_200(self, client: TestClient, caplog, monkeypatch):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        version = "v1.0.0"

        response = client.get(f"/versions/{urlquote(version)}/rulesets")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == version
        assert "rulesets" in data
        assert data["rulesets"] == [ ]

        assert "200" in caplog.text