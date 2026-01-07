"""
API-level unit tests for the Discovery endpoints
Tests how the service responds via HTTP under various conditions.
No direct instantiation of DiscoveryApiImpl — all via TestClient.
"""

import pytest
import respx
from httpx import Response
from fastapi.testclient import TestClient


class TestDiscoveryApi:

    test_repo_response = {
        "id": 123456789,
        "node_id": "R_kgDOABCDEF",
        "name": "test-repo",
        "full_name": "test-org/test-repo",
        "private": False,
        "owner": {
            "login": "test-org",
            "id": 987654,
            "type": "Organization"
        },
        "html_url": "https://github.com/test-org/test-repo",
        "description": "A test repository for CSIT validation",
        "fork": False,
        "url": "https://api.github.com/repos/test-org/test-repo",
        "created_at": "2025-11-15T10:00:00Z",
        "updated_at": "2026-01-08T14:30:00Z",
        "pushed_at": "2026-01-09T08:45:00Z",
        "git_url": "git://github.com/test-org/test-repo.git",
        "ssh_url": "git@github.com:test-org/test-repo.git",
        "clone_url": "https://github.com/test-org/test-repo.git",
        "size": 256,
        "stargazers_count": 5,
        "language": "Python",
        "has_issues": True,
        "open_issues_count": 2,
        "visibility": "public",
        "default_branch": "main"
    }

    test_tree_response = {
        "tree": [
            {"path": ".gitignore", "mode": "100644", "type": "blob"},
            {"path": "README.md", "mode": "100644", "type": "blob"},
            {"path": "STYLE_GUIDE.md", "mode": "100644", "type": "blob"},
            {"path": "extract-oas-rules.js", "mode": "100644", "type": "blob"},
            {"path": "generate_styleguide.py", "mode": "100755", "type": "blob"},
            {"path": "package.json", "mode": "100644", "type": "blob"},
            {"path": "spectral/basic-ruleset.yaml", "mode": "100644", "type": "blob"},
            {"path": "spectral/strict-ruleset.yaml", "mode": "100644", "type": "blob"},
            {"path": "spectral/sdx-ruleset.yaml", "mode": "100644", "type": "blob"},
            {"path": "tsconfig.json", "mode": "100644", "type": "blob"},
            {"path": "rulesets/security.yml", "mode": "100644", "type": "blob"},
            {"path": "rulesets/openapi.yml", "mode": "100644", "type": "blob"},
            {"path": "rulesets/extra.json", "mode": "100644", "type": "blob"},
            {"path": "docs/readme.md", "mode": "100644", "type": "blob"}
        ]
    }

    # ── Repository does not exist → 500 Internal Server Error ───────────────

    @respx.mock
    def test_list_versions_repo_not_found_500(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(404, json={"message": "Not Found"})

        response = client.get("/versions")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "does not exist or is inaccessible" in data["detail"].lower()

    # ── Private repo without token → 500 Internal Server Error ──────────────

    @respx.mock
    def test_list_versions_private_repo_500(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(403, json={"message": "Repository access blocked"})

        response = client.get("/versions")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "does not exist or is inaccessible" in data["detail"].lower()

    # ── Successful version list → 200 OK with sorted versions ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")  # ← if you want logs
    def test_list_versions_success_200(self, client: TestClient, caplog):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        # Mock tags include junk tags and are not in the correct semver
        mock_tags = [
            {"name": "ruleset-v1.0.0"},
            {"name": "junk-tag"},
            {"name": "ruleset-v1.2.3"},
            {"name": "ruleset-v1.3.0-Beta1"},
            {"name": "ruleset-v1.1.0"},
            {"name": "ruleset-vjunk-tag"},
            {"name": "ruleset-v1.3.0-beta1"},
            {"name": "ruleset-junk-tag"},
        ]
        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=mock_tags)

        response = client.get("/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert data["versions"] == ["v1.3.0-beta1","v1.3.0-Beta1","v1.2.3","v1.1.0","v1.0.0"]  # sorted newest first

        assert "200" in caplog.text

    # ── Empty version list → 200 OK with empty array ───────────────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_list_versions_empty_success_200(self, client: TestClient, caplog):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        # Mock tags include junk tags and are not in the correct semver
        mock_tags = []
        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=mock_tags)

        response = client.get("/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert data["versions"] == []  # empty

        assert "200" in caplog.text

    # Repository does not exist → 500 Internal Server Error
    @respx.mock
    def test_list_rulesets_repo_not_found_500(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(404, json={"message": "Not Found"})

        version = "v1.0.0"
        response = client.get(f"/versions/{version}/rulesets")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "does not exist or is inaccessible" in data["detail"].lower()

    # Private repo without token → 500 Internal Server Error
    @respx.mock
    def test_list_rulesets_private_repo_500(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(403, json={"message": "Repository access blocked"})

        version = "v1.0.0"
        response = client.get(f"/versions/{version}/rulesets")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "does not exist or is inaccessible" in data["detail"].lower()

    # Version (tag) not found → 404 Not Found
    @respx.mock
    def test_list_rulesets_version_not_found_404(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json=self.test_repo_response)

        version = "v1.3.0"

        # Bunch of tags but not the one we are looking for
        mock_tags = [
            {"name": "ruleset-v1.0.0"},
            {"name": "junk-tag"},
            {"name": "ruleset-v1.2.3"},
            {"name": "ruleset-v1.3.0-Beta1"},
            {"name": "ruleset-v1.1.0"},
            {"name": "ruleset-vjunk-tag"},
            {"name": "ruleset-v1.3.0-beta1"},
            {"name": "ruleset-junk-tag"},
            {"name": version}, # Does not have the prefix
        ]
        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=mock_tags)

        response = client.get(f"/versions/{version}/rulesets")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Version '{version}' not found" in data["detail"]
        assert "bcgov/csit-api-governance-spectral-style-guide" in data["detail"]

    # Successful ruleset list → 200 OK with sorted rulesets
    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_list_rulesets_success_200(self, client: TestClient, caplog):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json=self.test_repo_response)

        version = "v1.3.0"
        tag = f"ruleset-{version}" # This is our target tag

        mock_tags = [
            {"name": "ruleset-v1.0.0"},
            {"name": "junk-tag"},
            {"name": "ruleset-v1.2.3"},
            {"name": "ruleset-v1.3.0-Beta1"},
            {"name": "ruleset-v1.1.0"},
            {"name": "ruleset-vjunk-tag"},
            {"name": "ruleset-v1.3.0-beta1"},
            {"name": "ruleset-junk-tag"},
            {"name": tag},
        ]
        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=mock_tags)

        respx.get(f"https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/git/trees/{tag}?recursive=1") \
            .return_value = Response(200, json={
                "tree": [
                    {"path": ".gitignore", "mode": "100644", "type": "blob"},
                    {"path": "README.md", "mode": "100644", "type": "blob"},
                    {"path": "STYLE_GUIDE.md", "mode": "100644", "type": "blob"},
                    {"path": "extract-oas-rules.js", "mode": "100644", "type": "blob"},
                    {"path": "generate_styleguide.py", "mode": "100755", "type": "blob"},
                    {"path": "package.json", "mode": "100644", "type": "blob"},
                    {"path": "spectral/basic-ruleset.yaml", "mode": "100644", "type": "blob"},
                    {"path": "spectral/strict-ruleset.yaml", "mode": "100644", "type": "blob"},
                    {"path": "spectral/sdx-ruleset.yaml", "mode": "100644", "type": "blob"},
                    {"path": "tsconfig.json", "mode": "100644", "type": "blob"},
                    {"path": "rulesets/security.yml", "mode": "100644", "type": "blob"},
                    {"path": "rulesets/openapi.yml", "mode": "100644", "type": "blob"},
                    {"path": "rulesets/extra.json", "mode": "100644", "type": "blob"},
                    {"path": "docs/readme.md", "mode": "100644", "type": "blob"}
                ]
            })

        response = client.get(f"/versions/{version}/rulesets")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == version
        assert "rulesets" in data
        assert data["rulesets"] == [
            "basic-ruleset",
            "sdx-ruleset",
            "strict-ruleset"
        ]  # sorted alphabetically

        assert "200" in caplog.text

    # Successful ruleset list → 200 OK with no rulesets
    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_list_rulesets_empty_success_200(self, client: TestClient, caplog):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json=self.test_repo_response)

        version = "v1.3.0"
        tag = f"ruleset-{version}" # This is our target tag

        mock_tags = [
            {"name": "ruleset-v1.0.0"},
            {"name": "junk-tag"},
            {"name": "ruleset-v1.2.3"},
            {"name": "ruleset-v1.3.0-Beta1"},
            {"name": "ruleset-v1.1.0"},
            {"name": "ruleset-vjunk-tag"},
            {"name": "ruleset-v1.3.0-beta1"},
            {"name": "ruleset-junk-tag"},
            {"name": tag},
        ]
        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=mock_tags)

        respx.get(f"https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/git/trees/{tag}?recursive=1") \
            .return_value = Response(200, json={
                "tree": [
                    {"path": ".gitignore", "mode": "100644", "type": "blob"},
                    {"path": "README.md", "mode": "100644", "type": "blob"},
                    {"path": "STYLE_GUIDE.md", "mode": "100644", "type": "blob"},
                    {"path": "extract-oas-rules.js", "mode": "100644", "type": "blob"},
                    {"path": "generate_styleguide.py", "mode": "100755", "type": "blob"},
                    {"path": "package.json", "mode": "100644", "type": "blob"},
                    {"path": "tsconfig.json", "mode": "100644", "type": "blob"},
                    {"path": "rulesets/security.yml", "mode": "100644", "type": "blob"},
                    {"path": "rulesets/openapi.yml", "mode": "100644", "type": "blob"},
                    {"path": "rulesets/extra.json", "mode": "100644", "type": "blob"},
                    {"path": "docs/readme.md", "mode": "100644", "type": "blob"}
                ]
            })

        response = client.get(f"/versions/{version}/rulesets")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == version
        assert "rulesets" in data
        assert data["rulesets"] == [ ]

        assert "200" in caplog.text