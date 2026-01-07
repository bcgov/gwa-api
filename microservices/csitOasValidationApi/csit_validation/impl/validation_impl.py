# csit_validation/impl/validation_impl.py

import logging
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Tuple
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from starlette.requests import Request
from packaging import version
from csit_validation.apis.validation_api_base import BaseValidationApi
from csit_validation.apis.errors.problem_details import (
    ErrorItem,
    ErrorLocation,
    ProblemDetail,
    create_problem_response
)
from csit_validation.models.validation_response import (
    ValidationResponse,
    ValidationResponseSummary
)
from csit_validation.services.github_ruleset_service import GitHubRulesetService
from csit_validation.services.spectral_repo_cache import SpectralRepoCache
from csit_validation.util.log_decorator import log_entry_exit
from csit_validation.core.config import (
    GITHUB_TOKEN,
    GITHUB_REPO_OWNER,
    GITHUB_REPO_NAME,
    RULESET_DIRECTORY,
    RULESET_FILE_EXTENSIONS,
    GITHUB_TAG_CACHE_PATH,
)

logger = logging.getLogger(__name__)


class ValidationApiImpl(BaseValidationApi):
    """
    The Validation API endpoints support the validating of an OpenApi specification in json or yaml format, using 
    the version and ruleset discovered using the Discovery API.

    The GitHubRulesetService is used to versify the version and rulesets requested.

    The SpectralRepoCache is used to maintain a local cache of the rulesets from the https://github.com/bcgov/csit-api-governance-spectral-style-guide
    repository.

    Stoplight Spectral is used to perform the validation on the uploaded json or yaml OAS file.

    The service requires that both git and spectral command line interfaces have been installed.
    """

    @log_entry_exit(logger)
    def __init__(self):

        self.repo_owner = GITHUB_REPO_OWNER
        self.repo_name = GITHUB_REPO_NAME
        self.repo_token = GITHUB_TOKEN
        self.ruleset_dir = RULESET_DIRECTORY
        self.rules_file_extensions = RULESET_FILE_EXTENSIONS
        self.tag_prefix = "ruleset-"
        
        spectral_ver = self.get_spectral_version()

        if spectral_ver is None:
            logger.error("Could not determine Spectral version - assuming latest but proceed with caution")
        elif version.parse(spectral_ver) < version.parse("6.0.0"):
            logger.error(
                f"Unsupported Spectral version detected: {spectral_ver}\n"
                "This application requires Spectral >= 6.0.0 (breaking change in severity format).\n"
                "Please upgrade Spectral CLI."
            )
        else:
            logger.info(f"Using Spectral CLI version {spectral_ver}")
        
        self.gh = GitHubRulesetService(
            self.repo_owner,
            self.repo_name,
            self.repo_token,
            self.ruleset_dir,
            self.rules_file_extensions,
        )
            
        self._cache_dir = GITHUB_TAG_CACHE_PATH()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # We don't pass the GITHUB_TOKEN to the SpectralRepoCache becuase it uses subprocesses to make
        # git calls rather than via HTTPS requests.
        self.cache = SpectralRepoCache(
            self.repo_owner,
            self.repo_name,
            self._cache_dir,
            3600, # Clean up cache once per hour
        )

    @log_entry_exit(logger)
    def get_spectral_version(self) -> str | None:
        try:
            result = subprocess.run(
                ["spectral", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            # Output usually looks like: "6.14.2" or sometimes "@stoplight/spectral-cli/6.14.2 linux-x64 node-v20.17.0"
            output = result.stdout.strip()
            # Take first token that looks like semver
            for part in output.split():
                if part.count('.') >= 2 and part.replace('.', '').isdigit():
                    return part
            return output  # fallback - better than nothing
        except Exception as e:
            logger.warning(f"Could not determine Spectral version: {e}")
            return None

    @log_entry_exit(logger)
    async def _run_spectral_cli(
        self,
        document_content: bytes,
        ruleset_full_path: Path,
        content_type: str
    ) -> Tuple[bool, list[dict], ValidationResponseSummary, float]:

        suffix = ".json" if "json" in content_type else ".yaml"

        start_time = time.perf_counter()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(document_content)
            tmp_path = Path(tmp_file.name)

        try:
            cmd = [
                "spectral", "lint",
                "--format", "json",
                "--ruleset", str(ruleset_full_path),
                "--quiet",
                str(tmp_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000)

            if result.returncode not in (0, 1):
                logger.error(f"Spectral failed (code {result.returncode}):\n{result.stderr}")
                raise HTTPException(500, "Spectral validation engine internal error")

            output = json.loads(result.stdout) if result.stdout.strip() else []

            mapped_results = []
            counts = {"error": 0, "warn": 0, "info": 0, "hint": 0}

            severity_map = {0: "error", 1: "warn", 2: "info", 3: "hint"}

            for item in output:
                if not isinstance(item, dict):
                    continue

                raw = item.get("severity", 1)

                if isinstance(raw, int):
                    level = severity_map.get(raw, "unknown")
                else:
                    level = str(raw).lower()
                    if level == "warning":
                        level = "warn"

                if level in counts:
                    counts[level] += 1

                mapped_results.append({
                    "code": item.get("code"),
                    "message": item.get("message", "No message"),
                    "severity": level,
                    "path": item.get("path", []),
                    "range": item.get("range")
                })

                # Reverse lookup for sorting (string → numeric priority)
                severity_priority = {v: k for k, v in severity_map.items()}

                # After collecting all items
                mapped_results.sort(key=lambda r: (
                    severity_priority.get(r["severity"], 999),   # numeric priority (error first)
                    r["code"] or "",                             # alphabetical by code
                    tuple(r["path"] or [])                       # stable path comparison
                ))

            summary = ValidationResponseSummary(
                errors=counts["error"],
                warnings=counts["warn"],
                infos=counts["info"],
                hints=counts["hint"]
            )

            return summary.errors == 0, mapped_results, summary, duration_ms

        finally:
            tmp_path.unlink(missing_ok=True)


    @log_entry_exit(logger)
    async def create_validation(
        self,
        version: str,
        ruleset: str,
        request: Request
    ) -> ValidationResponse:

        await self.gh.ensure_repo_exists()

        prefixed_tag = await self.gh.get_tag_from_version(version)
        if prefixed_tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"Version '{version}' not found in {self.gh.repo_owner}/{self.gh.repo_name}"
            )

        ruleset_tuple = await self.gh.get_ruleset_tuple(prefixed_tag, ruleset)
        if ruleset_tuple is None:
            raise HTTPException(
                status_code=404,
                detail=f"Ruleset '{ruleset}' not found for Version '{version}' in {self.gh.repo_owner}/{self.gh.repo_name}"
            )

        _, ruleset_rel_path = ruleset_tuple
        logger.debug(f"ruleset_rel_path = {ruleset_rel_path}")

        raw_body = await request.body()
        if not raw_body.strip():
            problem = ProblemDetail(title="Bad Request", status=400)
            problem.add_error(ErrorItem(
                location=ErrorLocation.BODY,
                code="MISSING_BODY",
                message="Request body is required and cannot be empty"
            ))
            return create_problem_response(problem)

        content_type = request.headers.get("content-type", "").lower().split(";")[0].strip()
        allowed = {"application/json", "application/yaml"}
        if content_type not in allowed:
            problem = ProblemDetail(title="Unsupported Media Type", status=415)
            problem.add_error(ErrorItem(
                location=ErrorLocation.HEADER,
                field="content-type",
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Only JSON and YAML are supported",
                received=content_type or "missing"
            ))
            return create_problem_response(problem)

        # ── Main logic ───────────────────────────────────────────────

        logger.debug("<Processing request")

        cache_dir = self.cache.get_cache_dir_for_tag(prefixed_tag)
        cached_ruleset_path = cache_dir / ruleset_rel_path

        if not cached_ruleset_path.is_file():
            raise HTTPException(500, f"Cached ruleset file not found: {cached_ruleset_path}")

        lock = self.cache.get_tag_lock(prefixed_tag)
        logger.debug(f"lock = {lock}")
        lock.acquire_read()
        try:

            valid, results, summary, duration_ms = await self._run_spectral_cli(
                raw_body, cached_ruleset_path, content_type
            )

            logger.debug(">Processing request")

            return ValidationResponse(
                valid=valid,
                version=version,
                ruleset=ruleset,
                duration_ms=duration_ms,
                summary=summary,
                results=results,
                validated_at=datetime.now(timezone.utc)
            )
        
        finally:
            lock.release_read()