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
from fastapi.testclient import TestClient
from pathlib import Path
from csit_validation.core.config import get_github_tag_cache_path
from urllib.parse import quote

def urlquote(s: str) -> str:
    """Encode everything, including / → %2F (no safe characters)"""
    return quote(s, safe='')

logger = logging.getLogger(__name__)

class TestDiscoveryApi:

    test_version = "v1.1.0"

    test_ruleset = "sdx/ruleset"

    # ── Helper to locate resources directory ─────────────────────────────────
    @pytest.fixture(scope="class")
    def resources_dir(self):
        # From tests/unit/ → tests/ → resources/
        return Path(__file__).parent / "resources"

    # ── Version not found → 404 Not Found ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_version_not_found_404(
        self, 
        client: TestClient,
        resources_dir,
        monkeypatch,
    ):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        invalid_version = "v1.3.0-alpha"

        # -------------------------
        # Load OpenAPI spec
        # -------------------------
        spec_path = resources_dir / "test-oas-1.yaml"
        if not spec_path.exists():
            pytest.fail(f"OpenAPI spec file not found at: {spec_path}")

        openapi_content = spec_path.read_text(encoding="utf-8")

        response = client.post(
            f"/versions/{urlquote(invalid_version)}/rulesets/{urlquote(self.test_ruleset)}/validations",
            content=openapi_content.encode("utf-8"),
            headers={"Content-Type": "application/yaml"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Version '{invalid_version}' not found" in data["detail"]

    # ── Ruleset not found → 404 Not Found ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_ruleset_not_found_404(
        self, 
        client: TestClient,
        resources_dir,
        monkeypatch,
    ):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()
        
        invalid_ruleset = "invalid-ruleset"

        # -------------------------
        # Load OpenAPI spec
        # -------------------------
        spec_path = resources_dir / "test-oas-1.yaml"
        if not spec_path.exists():
            pytest.fail(f"OpenAPI spec file not found at: {spec_path}")

        openapi_content = spec_path.read_text(encoding="utf-8")

        response = client.post(
            f"/versions/{urlquote(self.test_version)}/rulesets/{urlquote(invalid_ruleset)}/validations",
            content=openapi_content.encode("utf-8"),
            headers={"Content-Type": "application/yaml"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Ruleset '{invalid_ruleset}' not found for Version '{self.test_version}'" in data["detail"]
        
    # ── Request missing body → 400 Bad Request ──────────────

    @respx.mock
    @pytest.mark.usefixtures("enable_http_logging", "http_debug")
    def test_create_validation_missing_body_400(
        self, 
        client: TestClient,
        monkeypatch,
    ):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        response = client.post(f"/versions/{urlquote(self.test_version)}/rulesets/{urlquote(self.test_ruleset)}/validations")

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
    def test_create_validation_unsupported_content_type_415(
        self, 
        client: TestClient,
        monkeypatch,
    ):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

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
            f"/versions/{urlquote(self.test_version)}/rulesets/{urlquote(self.test_ruleset)}/validations",
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
        monkeypatch,
    ):

        cache_dir = Path(__file__).parent / "resources" / "github-cache"
        monkeypatch.setenv("GITHUB_TAG_CACHE_PATH", str(cache_dir.resolve()))

        # Invalidate the cache so next read sees the new env value
        get_github_tag_cache_path.cache_clear()

        # -------------------------
        # Load OpenAPI spec
        # -------------------------
        spec_path = resources_dir / "test-oas-1.yaml"
        if not spec_path.exists():
            pytest.fail(f"OpenAPI spec file not found at: {spec_path}")

        openapi_content = spec_path.read_text(encoding="utf-8")

        # -------------------------
        # Make API request
        # -------------------------

        response = client.post(
            f"/versions/{urlquote(self.test_version)}/rulesets/{urlquote(self.test_ruleset)}/validations",
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
        assert data["ruleset"] == self.test_ruleset

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

