"""
API-level unit tests for the Validation endpoints
Tests how the service responds via HTTP under various conditions.
No direct instantiation of ValidationApiImpl — all via TestClient.
"""

import logging
import pytest
import respx
import textwrap
from pathlib import Path
from httpx import Response
from fastapi.testclient import TestClient




from unittest.mock import patch
from pathlib import Path
import pytest
from httpx import Response

logger = logging.getLogger(__name__)

class TestDiscoveryApi:

    test_repo_response = {
        "id": 123456789,
        "node_id": "R_kgDOABCDEF",
        "name": "csit-api-governance-spectral-style-guide",
        "full_name": "bcgov/csit-api-governance-spectral-style-guide",
        "private": False,
        "owner": {
            "login": "test-org",
            "id": 987654,
            "type": "Organization"
        },
        "html_url": "https://github.com/bcgov/csit-api-governance-spectral-style-guide",
        "description": "A test repository for CSIT validation",
        "fork": False,
        "url": "https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide",
        "created_at": "2025-11-15T10:00:00Z",
        "updated_at": "2026-01-08T14:30:00Z",
        "pushed_at": "2026-01-09T08:45:00Z",
        "git_url": "git://github.com/bcgov/csit-api-governance-spectral-style-guide.git",
        "ssh_url": "git@github.com:bcgov/csit-api-governance-spectral-style-guide.git",
        "clone_url": "https://github.com/bcgov/csit-api-governance-spectral-style-guide.git",
        "size": 256,
        "stargazers_count": 5,
        "language": "Python",
        "has_issues": True,
        "open_issues_count": 2,
        "visibility": "public",
        "default_branch": "main"
    }

    test_version = "v1.3.0"
    test_tag = f"ruleset-{test_version}"

    test_tags_reponse = [
        {"name": "ruleset-v1.0.0"},
        {"name": "ruleset-v1.1.0"},
        {"name": "ruleset-v1.2.3"},
        {"name": test_tag},
    ]

    test_ruleset_1 = "test-ruleset-1"
    test_ruleset_2 = "test-ruleset-2"
    test_ruleset_3 = "test-ruleset-3"

    test_tree_response = {
        "tree": [
            {"path": ".gitignore", "mode": "100644", "type": "blob"},
            {"path": "README.md", "mode": "100644", "type": "blob"},
            {"path": "STYLE_GUIDE.md", "mode": "100644", "type": "blob"},
            {"path": "extract-oas-rules.js", "mode": "100644", "type": "blob"},
            {"path": "generate_styleguide.py", "mode": "100755", "type": "blob"},
            {"path": "package.json", "mode": "100644", "type": "blob"},
            {"path": f"spectral/{test_ruleset_1}.yaml", "mode": "100644", "type": "blob"},
            {"path": f"spectral/{test_ruleset_2}.yaml", "mode": "100644", "type": "blob"},
            {"path": f"spectral/{test_ruleset_3}.yaml", "mode": "100644", "type": "blob"},
            {"path": "tsconfig.json", "mode": "100644", "type": "blob"},
            {"path": "rulesets/security.yml", "mode": "100644", "type": "blob"},
            {"path": "rulesets/openapi.yml", "mode": "100644", "type": "blob"},
            {"path": "rulesets/extra.json", "mode": "100644", "type": "blob"},
            {"path": "docs/readme.md", "mode": "100644", "type": "blob"}
        ]
    }


    # We need to override the cache path for the tests so we are using our
    # mocked cache in the resources and not a temp directory.
    @pytest.fixture(autouse=True)
    def set_tag_cache_path(self, monkeypatch, resources_dir):

        cache_path = resources_dir / "github.com/bcgov/csit-api-governance-spectral-style-guide"
        if not cache_path.exists():
            pytest.fail(f"Cache not found at: {cache_path}")

        # -------------------------
        # Set environment variables
        # -------------------------
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", f"{cache_path}")

    # ── Helper to locate resources directory ─────────────────────────────────
    @pytest.fixture(scope="class")
    def resources_dir(self):
        # From tests/unit/ → tests/ → resources/
        return Path(__file__).parent.parent / "resources"

    # ── Repository does not exist → 500 Internal Server Error ───────────────

    @respx.mock
    def test_create_validation_repo_not_found_500(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(404, json={"message": "Not Found"})

        # TODO Add Body

        response = client.post(f"/versions/{self.test_version}/rulesets/{self.test_ruleset_1}/validations")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "does not exist or is inaccessible" in data["detail"].lower()

    # ── Private repo without token → 500 Internal Server Error ──────────────

    @respx.mock
    def test_create_validation_private_repo_500(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(403, json={"message": "Repository access blocked"})

        # TODO Add Body

        response = client.post(f"/versions/{self.test_version}/rulesets/{self.test_ruleset_1}/validations")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "does not exist or is inaccessible" in data["detail"].lower()

    # ── Version not found → 404 Not Found ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_version_not_found_404(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=self.test_tags_reponse)

        invalid_version = "v1.3.0-alpha"

        # TODO Add Body

        response = client.post(f"/versions/{invalid_version}/rulesets/{self.test_ruleset_1}/validations")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Version '{invalid_version}' not found in bcgov/csit-api-governance-spectral-style-guide" in data["detail"]

    # ── Ruleset not found → 404 Not Found ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_ruleset_not_found_404(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=self.test_tags_reponse)

        respx.get(f"https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/git/trees/{self.test_tag}?recursive=1") \
            .return_value = Response(200, json=self.test_tree_response)
        
        invalid_ruleset = "invalid-ruleset"

        # TODO Add Body

        response = client.post(f"/versions/{self.test_version}/rulesets/{invalid_ruleset}/validations")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Ruleset '{invalid_ruleset}' not found for Version '{self.test_version}' in bcgov/csit-api-governance-spectral-style-guide" in data["detail"]
        
    # ── Request missing body → 400 Bad Request ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_missing_body_400(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=self.test_tags_reponse)

        respx.get(f"https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/git/trees/{self.test_tag}?recursive=1") \
            .return_value = Response(200, json=self.test_tree_response)

        response = client.post(f"/versions/{self.test_version}/rulesets/{self.test_ruleset_1}/validations")

        assert response.status_code == 400
        problem = response.json()

        # Check required RFC 9457 fields
        assert problem["type"] == "tag:validation-errors"
        assert problem["title"] == "Bad Request"
        assert problem["status"] == 400

        # Check the errors array
        assert "errors" in problem, "Problem detail should contain 'errors' array"
        assert len(problem["errors"]) == 1, "Expected exactly one error for missing body"

        error = problem["errors"][0]

        # Validate the individual error item
        assert error["location"] == "body"
        assert error["code"] == "MISSING_BODY"
        assert error["message"] == "Request body is required and cannot be empty"
        assert error["type"] == "tag:validation-error"

        # Optional: check that no unnecessary fields are present
        assert "field" not in error, "field should not be present for body-level errors"
        assert "received" not in error, "received should not be present when body is missing"

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_unsupported_content_type_415(self, client: TestClient):

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=self.test_tags_reponse)

        respx.get(f"https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/git/trees/{self.test_tag}?recursive=1") \
            .return_value = Response(200, json=self.test_tree_response)

        # Properties file
        properties_content = textwrap.dedent("""\
            # Database connection settings
            db.host=localhost
            db.port=5432
            db.name=app_production
            db.user=app_user
        """).strip() 

        # Send as application/x-java-properties
        response = client.post(
            f"/versions/{self.test_version}/rulesets/{self.test_ruleset_1}/validations",
            content=properties_content.encode("utf-8"),
            headers={
                "Content-Type": "application/x-java-properties"
            }
        )

        # Expect 415 Unsupported Media Type
        assert response.status_code == 415

        problem = response.json()

        # Check required RFC 9457 fields
        assert problem["type"] == "tag:validation-errors"
        assert problem["title"] == "Unsupported Media Type"
        assert problem["status"] == 415

        # Check the errors array
        assert "errors" in problem, "Problem detail should contain 'errors' array"
        assert len(problem["errors"]) == 1, "Expected exactly one error for unsupported media type"

        error = problem["errors"][0]

        # Validate the individual error item
        assert error["location"] == "header"
        assert error["code"] == "UNSUPPORTED_MEDIA_TYPE"
        assert error["message"] == "Only JSON and YAML are supported"
        assert error["type"] == "tag:validation-error"
        assert error["field"] == "content-type"
        assert error["received"] == "application/x-java-properties"

        # Optional: check no irrelevant fields
        assert "pointer" not in error, "pointer should not be present for header errors"

    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    @respx.mock
    def test_create_validation_success_200(
        self,
        client: "TestClient",
        resources_dir,
    ):

        # -------------------------
        # Mock GitHub API responses
        # -------------------------
        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide") \
            .return_value = Response(200, json={"message": self.test_repo_response})

        respx.get("https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/tags") \
            .return_value = Response(200, json=self.test_tags_reponse)

        respx.get(f"https://api.github.com/repos/bcgov/csit-api-governance-spectral-style-guide/git/trees/{self.test_tag}?recursive=1") \
            .return_value = Response(200, json=self.test_tree_response)

        # -------------------------
        # Load OpenAPI spec
        # -------------------------
        spec_path = resources_dir / "test-oas-1.yaml"
        if not spec_path.exists():
            pytest.fail(f"OpenAPI spec file not found at: {spec_path}")

        openapi_content = spec_path.read_text(encoding="utf-8")

        # -------------------------
        # Mock subprocess calls
        # -------------------------
        with patch("csit_validation.services.spectral_repo_cache.subprocess.check_call") as mock_check_call, \
            patch("csit_validation.services.spectral_repo_cache.subprocess.check_output") as mock_check_output:

            # check_call: simulate worktree creation and sparse checkout
            def fake_check_call(*args, **kwargs):
                cmd = args[0] if args else []
                logger.debug(f"fake_check_call cmd {cmd}")

                if "worktree" in cmd:
                    tag_dir = Path(cmd[3])
                    (tag_dir / "spectral").mkdir(parents=True, exist_ok=True)
                return 0

            mock_check_call.side_effect = fake_check_call

            # check_output: simulate git tag listing and rev-parse
            def fake_check_output(args, cwd=None, text=True):
                if args[:2] == ["git", "rev-parse"]:
                    return self.test_tag
                if args[:2] == ["git", "tag"]:
                    return f"{self.test_tag}\n"
                return ""

            mock_check_output.side_effect = fake_check_output

            # -------------------------
            # Make API request
            # -------------------------
            response = client.post(
                f"/versions/{self.test_version}/rulesets/{self.test_ruleset_1}/validations",
                content=openapi_content.encode("utf-8"),
                headers={"Content-Type": "application/yaml"}
            )

            # -------------------------
            # Assertions
            # -------------------------
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()

            # Basic structure
            assert data["valid"] is False
            assert data["version"] == self.test_version
            assert data["ruleset"] == self.test_ruleset_1

            # Summary counts - match your latest response
            summary = data["summary"]
            assert summary["errors"] == 1,   f"Expected 1 error, got {summary['errors']}"
            assert summary["warnings"] == 1, f"Expected 1 warning, got {summary['warnings']}"
            assert summary["infos"] == 2,    f"Expected 2 infos, got {summary['infos']}"
            assert summary["hints"] == 1,    f"Expected 1 hint, got {summary['hints']}"
            
            # Results array
            results = data["results"]
            assert len(results) == 5

            index = 0
            # Result 3 - parser (error)
            assert results[index]["code"] == "parser"
            assert results[index]["message"] == "Mapping key must be a string scalar rather than number"
            assert results[index]["severity"] == "error"
            assert results[index]["path"] == ["paths", "/users", "post", "responses", "201"]

            index = index + 1
            # Result 4 - operation-tags (warn)
            assert results[index]["code"] == "operation-tags"
            assert results[index]["message"] == "Operation must have non-empty \"tags\" array."
            assert results[index]["severity"] == "warn"
            assert results[index]["path"] == ["paths", "/users/{id}", "get"]

            index = index + 1
            # Result 2 - operation-id-camel-case (info)
            assert results[index]["code"] == "operation-id-camel-case"
            assert results[index]["message"] == "operationId should be camelCase (starts with lowercase letter, no separators)"
            assert results[index]["severity"] == "info"
            assert results[index]["path"] == ["paths", "/users", "post", "operationId"]

            index = index + 1
            # Result 5 - operation-id-camel-case (info)
            assert results[index]["code"] == "operation-id-camel-case"
            assert results[index]["message"] == "operationId should be camelCase (starts with lowercase letter, no separators)"
            assert results[index]["severity"] == "info"
            assert results[index]["path"] == ["paths", "/users/{id}", "get", "operationId"]

            index = index + 1
            # Result 1 - info-description (hint)
            assert results[index]["code"] == "info-description"
            assert results[index]["message"] == "Info \"description\" must be present and non-empty string."
            assert results[index]["severity"] == "hint"
            assert results[index]["path"] == ["info"]

            # Optional: ensure mocked calls were made
            mock_check_call.assert_called()
            mock_check_output.assert_called()

