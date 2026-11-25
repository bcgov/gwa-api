"""
API-level unit tests for the readiness and health endpoints.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from csit_validation.core.config import get_github_tag_cache_path

FIXTURE_CACHE_DIR = (Path(__file__).parent / "resources" / "github-cache").resolve()


@pytest.fixture
def use_cache(monkeypatch):
    def _use(path: Path):
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(path))
        get_github_tag_cache_path.cache_clear()

    yield _use
    get_github_tag_cache_path.cache_clear()


class TestReadyz:

    def test_ready_when_versions_available(self, client: TestClient, use_cache):
        use_cache(FIXTURE_CACHE_DIR)

        response = client.get("/readyz")

        assert response.status_code == 200

    def test_not_ready_without_versions(self, client: TestClient, use_cache, tmp_path):
        use_cache(tmp_path / "empty-cache")

        response = client.get("/readyz")

        assert response.status_code == 503
        assert response.json()["detail"] == "No ruleset versions available"


class TestHealth:

    def test_reports_versions_with_fetched_commits(self, client: TestClient, use_cache, tmp_path):
        cache = tmp_path / "cache"
        (cache / "tags" / "ruleset-v1.1.0" / "dist" / "spectral").mkdir(parents=True)
        (cache / "manifest.json").write_text(json.dumps({
            "repository": "https://github.com/bcgov/itk-api-governance.git",
            "prefixes": ["ruleset-"],
            "fetched_at": "2026-11-25T00:00:00Z",
            "tags": {"ruleset-v1.1.0": "0123456789abcdef0123456789abcdef01234567"},
        }))
        use_cache(cache)

        response = client.get("/health")

        assert response.status_code == 200
        rulesets = response.json()["components"]["rulesets"]
        assert rulesets["status"] == "healthy"
        assert rulesets["repository"] == "https://github.com/bcgov/itk-api-governance.git"
        assert rulesets["fetched_at"] == "2026-11-25T00:00:00Z"
        assert rulesets["versions"] == {
            "v1.1.0": {"tag": "ruleset-v1.1.0", "commit": "0123456789abcdef0123456789abcdef01234567"},
        }

    def test_unhealthy_without_versions(self, client: TestClient, use_cache, tmp_path):
        use_cache(tmp_path / "empty-cache")

        response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "unhealthy"
        assert "no ruleset versions available" in body["message"].lower()
        assert body["components"]["rulesets"]["status"] == "unhealthy"
        assert body["components"]["rulesets"]["versions"] == {}
