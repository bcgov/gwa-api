import importlib
import pkgutil

from csit_validation.apis.discovery_api_base import BaseDiscoveryApi
import csit_validation.impl

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
)

from pydantic import Field, StrictStr
from typing_extensions import Annotated
from csit_validation.apis.errors.error_response import ErrorResponse
from csit_validation.models.ruleset_list import RulesetList
from csit_validation.models.version_list import VersionList


router = APIRouter()

ns_pkg = csit_validation.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/versions",
    operation_id="listVersions",
    responses={
        200: {"model": VersionList, "description": "Successful response"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Discovery"],
    summary="List available versions of the API Governance rules",
    response_model_by_alias=True,
)
async def list_versions(
) -> VersionList:
    """Returns all Git tags (versions) from the csit-api-governance-spectral-style-guide repository which contain Spectral rulesets."""
    if not BaseDiscoveryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDiscoveryApi.subclasses[0]().list_versions()


@router.get(
    "/versions/{version}/rulesets",
    operation_id="listRulesets",
    responses={
        200: {"model": RulesetList, "description": "Successful response"},
        404: {"model": ErrorResponse, "description": "Version or ruleset not found"},
        422: {
            "description": "Validation Error (automatically added by FastAPI)",
            "x-remove": True  # ← Custom flag to mark for removal
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Discovery"],
    summary="List Spectral rulesets in a version",
    response_model_by_alias=True,
)
async def list_rulesets_in_version(
    version: Annotated[StrictStr, Field(description="Version (Git tag) name")] = Path(..., description="Version (Git tag) name", examples=["v1.0.0"]),
) -> RulesetList:
    """Returns the list of Spectral rulesets available in the specified version."""
    if not BaseDiscoveryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDiscoveryApi.subclasses[0]().list_rulesets_in_version(version)
