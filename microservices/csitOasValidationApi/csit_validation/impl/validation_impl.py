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
from fastapi.responses import JSONResponse
from starlette.requests import Request
from packaging import version
from csit_validation.apis.validation_api_base import BaseValidationApi

from csit_validation.apis.errors.problem_detail_error_item import ProblemDetailErrorItem
from csit_validation.apis.errors.problem_detail_error_location import ProblemDetailErrorLocation
from csit_validation.apis.errors.problem_detail_response import ProblemDetailResponse
from csit_validation.models.validation_response import (
    ValidationResponse,
    ValidationResponseSummary
)
from csit_validation.services.cached_rulesets_service import CachedRulesetsService
from csit_validation.util.log_decorator import log_entry_exit
from csit_validation.core.config import (
    VERSION_TAG_PREFIX,
    RULESET_DIRECTORY,
    GITHUB_TAG_CACHE_PATH,
)

logger = logging.getLogger(__name__)


class ValidationApiImpl(BaseValidationApi):
    """
    The Validation API endpoints support the validating of an OpenApi specification in json or yaml format, using 
    the version and ruleset discovered using the Discovery API.

    The GitHubRulesetService is used to verify the version and rulesets requested.

    Stoplight Spectral is used to perform the validation on the uploaded json or yaml OAS file.

    The service requires that both git and spectral command line interfaces have been installed.
    """

    @log_entry_exit(logger)
    def __init__(self):

        self.github_tag_cache_path = GITHUB_TAG_CACHE_PATH
        self.version_tag_prefix = VERSION_TAG_PREFIX
        self.ruleset_dir = RULESET_DIRECTORY
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
        
        self.gh = CachedRulesetsService(
            self.github_tag_cache_path,
            self.version_tag_prefix,
            self.ruleset_dir,
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

            # Write output to temporary files to avoid pipe buffer size limits (64KB default on many systems)
            # This ensures we can capture arbitrarily large outputs from Spectral
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_output:
                output_path = Path(tmp_output.name)
            with tempfile.NamedTemporaryFile(suffix='.err', delete=False) as tmp_error:
                error_path = Path(tmp_error.name)

            try:
                # Run spectral and redirect output to files to avoid buffer limits
                with open(output_path, 'w', encoding='utf-8') as out_file, \
                     open(error_path, 'w', encoding='utf-8') as err_file:
                    process = subprocess.Popen(
                        cmd,
                        stdout=out_file,
                        stderr=err_file,
                        text=True
                    )
                    
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        raise HTTPException(500, "Spectral validation timed out after 30 seconds")
                
                # Read the output files after process completes
                with open(output_path, 'r', encoding='utf-8') as out_file:
                    stdout = out_file.read()
                
                with open(error_path, 'r', encoding='utf-8') as err_file:
                    stderr = err_file.read()
            finally:
                # Clean up temporary output files
                output_path.unlink(missing_ok=True)
                error_path.unlink(missing_ok=True)

            duration_ms = round((time.perf_counter() - start_time) * 1000)

            if process.returncode not in (0, 1):
                logger.error(f"Spectral failed (code {process.returncode}):\n{stderr}")
                raise HTTPException(500, "Spectral validation engine internal error")

            # Parse JSON output, handling empty or whitespace-only output
            stdout_stripped = stdout.strip() if stdout else ""
            if not stdout_stripped:
                output = []
            else:
                try:
                    output = json.loads(stdout_stripped)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse Spectral JSON output. "
                        f"Error: {e}. "
                        f"Output length: {len(stdout_stripped)} chars. "
                        f"First 500 chars: {stdout_stripped[:500]}"
                    )
                    # Log the problematic area around the error
                    if e.pos is not None:
                        start_pos = max(0, e.pos - 200)
                        end_pos = min(len(stdout_stripped), e.pos + 200)
                        logger.error(
                            f"Context around error position {e.pos}: "
                            f"{stdout_stripped[start_pos:end_pos]}"
                        )
                    raise HTTPException(
                        500,
                        f"Spectral output parsing failed: {str(e)}. "
                        f"The output may have been truncated or malformed."
                    )

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

        version_to_tag_map = self.gh.get_valid_version_tags
        prefixed_tag = version_to_tag_map.get(version)
        if prefixed_tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"Version '{version}' not found"
            )

        ruleset_tuple = await self.gh.get_ruleset_tuple(prefixed_tag, ruleset)
        if ruleset_tuple is None:
            raise HTTPException(
                status_code=404,
                detail=f"Ruleset '{ruleset}' not found for Version '{version}'"
            )

        _, ruleset_rel_path = ruleset_tuple
        logger.debug(f"ruleset_rel_path = {ruleset_rel_path}")

        raw_body = await request.body()
        if not raw_body.strip():

            return JSONResponse(
                status_code=400,
                content=ProblemDetailResponse(
                    type = "tag:validation-errors",
                    title = "Bad Request",
                    status = 400,
                    errors = [
                        ProblemDetailErrorItem(
                            type = "tag:validation-error",
                            location = ProblemDetailErrorLocation.BODY,
                            code = "MISSING_BODY",
                            message = "Request body is required and cannot be empty"
                        )
                    ]
                ).model_dump(
                    mode="json",
                    exclude_none=True)
                )


        content_type = request.headers.get("content-type", "").lower().split(";")[0].strip()
        allowed = {"application/json", "application/yaml"}
        if content_type not in allowed:

            return JSONResponse(
                status_code=415,
                content=ProblemDetailResponse(
                    type = "tag:validation-errors",
                    title = "Unsupported Media Type",
                    status = 415,
                    errors = [
                        ProblemDetailErrorItem(
                            type = "tag:validation-error",
                            location = ProblemDetailErrorLocation.HEADER,
                            field = "content-type",
                            code = "UNSUPPORTED_MEDIA_TYPE",
                            message = "Only JSON and YAML are supported",
                            received = content_type or "missing"
                        )
                    ]
                ).model_dump(
                    mode="json",
                    exclude_none=True)
                )

        # ── Main logic ───────────────────────────────────────────────

        logger.debug("<Processing request")

        cache_dir = Path(self.github_tag_cache_path()) / "tags" / prefixed_tag
        cached_ruleset_path = cache_dir / ruleset_rel_path
        logger.debug(f"cached_ruleset_path={cached_ruleset_path}")

        if not cached_ruleset_path.is_file():
            raise HTTPException(500, f"Cached ruleset file not found: {cached_ruleset_path}")

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