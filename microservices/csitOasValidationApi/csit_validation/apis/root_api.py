import importlib
import pkgutil

from csit_validation.apis.root_api_base import BaseRootApi
import csit_validation.impl

from fastapi import (
    APIRouter,
    HTTPException,
)
from csit_validation.models.health import HealthResponse
from csit_validation.apis.errors.error_response import ErrorResponse

from pydantic import StrictStr


router = APIRouter()

ns_pkg = csit_validation.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/",
    responses={
        307: {"description": "Temporary Redirect to API documentation"},
    },
    tags=["Info"],
    summary="Root endpoint - redirects to API documentation",
    response_model_by_alias=True,
)
async def root() -> str:
    """Redirects the root URL (/) to the interactive API documentation (/docs)."""
    if not BaseRootApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRootApi.subclasses[0]().root()


@router.get(
    "/livez",
    responses={
        200: {"model": StrictStr, "description": "Successful response"},
    },
    tags=["Liveness"],
    summary="Kubernetes liveness probe",
    response_model_by_alias=True,
)
async def livez() -> str:
    """Liveness probe - returns 200 if the FastAPI process is alive and responding."""
    if not BaseRootApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRootApi.subclasses[0]().livez()


@router.get(
    "/readyz",
    responses={
        200: {"model": StrictStr, "description": "Successful response"},
    },
    tags=["Ready"],
    summary="Kubernetes readiness probe",
    response_model_by_alias=True,
)
async def readyz() -> str:
    """Readiness probe - returns 200 only when the service can meaningfully serve traffic (at least one discovery implementation is loaded)."""
    if not BaseRootApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRootApi.subclasses[0]().readyz()


@router.get(
    "/health",
    responses={
        200: {"model": HealthResponse, "description": "Detailed service health status"},
        500: {"model": ErrorResponse, "description": "No implementation available"},
    },
    tags=["Health"],
    summary="Detailed health check endpoint",
    response_model_by_alias=True,
)
async def health() -> HealthResponse:
    """
    Health check endpoint returning structured service health information.

    This endpoint provides more detailed health information than the binary
    /livez and /readyz probes. It is suitable for:
    - External monitoring tools
    - Status dashboards
    - Debugging and alerting

    Returns:
        HealthStatus: An object/enum indicating overall health (healthy/degraded/unhealthy)
                      along with optional message, components, etc.

    Raises:
        HTTPException(500): If no BaseRootApi implementation is registered
    """
    if not BaseRootApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRootApi.subclasses[0]().health()
