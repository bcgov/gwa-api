# csit_validation/impl/root_impl.py

import logging
import shutil
import asyncio
from datetime import datetime
from fastapi import (
    HTTPException,
    status
)
from fastapi.responses import RedirectResponse

from csit_validation.apis.root_api_base import BaseRootApi
from csit_validation.models.health import (
     HealthStatus,
     HealthResponse,
)

logger = logging.getLogger(__name__)


class RootApiImpl(BaseRootApi):
    """
    Abstract base class for root/info/health endpoints implementations.
    
    Concrete subclasses should be placed in csit_validation.impl.* 
    and will be auto-discovered via pkgutil.
    """

    async def root(self) -> str:
        """Redirects the root URL (/) to the interactive API documentation (/docs)."""
        logger.debug("<root")
        return RedirectResponse(
            url="/docs",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    async def livez(self) -> str:
            """
            Default liveness check: just confirm the process is responding.
            
            This should be extremely cheap — no I/O, no external dependencies.
            Override only if you have very lightweight in-memory state to verify.
            """
            logger.debug("<livez")
            return "ok"
    
    async def readyz(self, version: str | None = None) -> str:
            """
            Default readiness check: confirm at least one implementation is loaded.
            """
            logger.debug("<readyz")
            # Minimal check: if we're here, the app has started and subclasses exist
            if not self.subclasses:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No root API implementation available"
                )
            return "ok"
    
    async def health(self) -> HealthResponse:
        """
        Detailed health check that verifies Stoplight Spectral is installed and functional.

        Checks:
        - Presence of 'spectral' CLI in PATH
        - Successful execution of 'spectral --version'

        Returns HealthResponse with component-level detail for "spectral".
        """
        logger.debug("<health - checking Spectral availability")

        now = datetime.utcnow()
        timestamp = now.isoformat() + "Z"

        # Default to healthy – only downgrade on failure
        overall_status = HealthStatus.HEALTHY
        overall_message = "Service operational"

        spectral_status = "healthy"
        spectral_message = "Spectral CLI is available and functional"
        spectral_details: dict[str, str] = {}

        spectral_path = shutil.which("spectral")

        if spectral_path is None:
            logger.warning("Stoplight Spectral CLI not found in PATH")
            spectral_status = "unhealthy"
            spectral_message = "Spectral CLI not installed or not in PATH"
            overall_status = HealthStatus.UNHEALTHY
            overall_message = "Critical dependency missing: Stoplight Spectral"

        else:
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    "spectral",
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = await proc.communicate()
                return_code = proc.returncode

                if return_code != 0:
                    error_output = stderr_bytes.decode().strip() or "(no stderr)"
                    logger.warning(
                        f"Spectral --version failed (code {return_code}): {error_output}"
                    )
                    spectral_status = "degraded"
                    spectral_message = f"Spectral found but --version failed (exit {return_code})"
                    overall_status = HealthStatus.DEGRADED
                    overall_message = "Service degraded - Spectral CLI not functional"
                else:
                    version_output = stdout_bytes.decode().strip()
                    spectral_details["version"] = version_output
                    logger.debug(f"Spectral version: {version_output}")

            except Exception as exc:
                logger.warning(f"Failed to run spectral --version: {exc}")
                spectral_status = "degraded"
                spectral_message = f"Spectral found but execution failed: {str(exc)}"
                overall_status = HealthStatus.DEGRADED
                overall_message = "Service degraded - Spectral CLI execution issue"

        # Build components
        components = {
            "spectral": {
                "status": spectral_status,
                "message": spectral_message,
                **spectral_details,
            }
        }

        response = HealthResponse(
            status=overall_status,
            message=overall_message,
            timestamp=timestamp,
            components=components,
        )

        logger.debug(f"Health check completed: {overall_status.value}")
        return response