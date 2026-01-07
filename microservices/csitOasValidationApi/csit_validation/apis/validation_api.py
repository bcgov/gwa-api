import importlib
import pkgutil

from csit_validation.apis.validation_api_base import BaseValidationApi
import csit_validation.impl

from fastapi import (  # noqa: F401
    APIRouter,
    HTTPException,
    Path,
    Request
)

from pydantic import Field, StrictStr
from typing_extensions import Annotated
from csit_validation.apis.errors.error_response import ErrorResponse
from csit_validation.models.validation_response import ValidationResponse


router = APIRouter()

ns_pkg = csit_validation.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)

EXAMPLE_OAS_JSON = """{
  "openapi": "3.1.0",
  "info": {
    "title": "Pet Store API",
    "version": "1.0.0",
    "description": "A simple example API for managing pets"
  },
  "paths": {
    "/pets": {
      "get": {
        "summary": "List all pets",
        "operationId": "listPets",
        "responses": {
          "200": {
            "description": "A list of pets",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Pet"
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Pet": {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
          "id": { "type": "integer" },
          "name": { "type": "string" },
          "tag": { "type": "string" }
        }
      }
    }
  }
}
"""

EXAMPLE_OAS_YAML = """openapi: 3.1.0
info:
  title: Pet Store API
  version: 1.0.0
  description: A simple example API for managing pets
paths:
  /pets:
    get:
      summary: List all pets
      operationId: listPets
      responses:
        '200':
          description: A list of pets
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Pet'
components:
  schemas:
    Pet:
      type: object
      required:
        - id
        - name
      properties:
        id:
          type: integer
        name:
          type: string
        tag:
          type: string
"""

@router.post(
    "/versions/{version}/rulesets/{ruleset}/validations",
    operation_id="createValidation",
    responses={
        200: {"model": ValidationResponse, "description": "Validation completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request (missing file, unsupported format, etc.)"},
        404: {"model": ErrorResponse, "description": "Version or ruleset not found"},
        422: {"model": ErrorResponse, "description": "OAS document could not be parsed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Validation"],
    summary="Validate an OpenAPI document",
    response_model_by_alias=True,
    # We are unable to use the annotations to generate the OpenApi request body as desired so we are providing the
    # definition manually.
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": "The raw OpenAPI document to validate. Send as JSON or YAML with appropriate Content-Type header.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                        "description": "OpenAPI document in JSON format"
                    },
                    "examples": {
                        "pet-store-json": {
                            "summary": "An example JSON Open API specification",
                            "value": EXAMPLE_OAS_JSON
                        }
                    }
                },
                "application/yaml": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                        "description": "OpenAPI document in YAML format"
                    },
                    "examples": {
                        "pet-store-yaml": {
                            "summary": "An example YAML Open API specification",
                            "value": EXAMPLE_OAS_YAML
                        }
                    }
                }
            }
        },
    },
)
async def create_validation(
    version: Annotated[StrictStr, Field(description="Version (Git tag) name")] = Path(..., description="Version (Git tag) name", examples=["v1.0.0"]),
    ruleset: Annotated[StrictStr, Field(description="Path to the Spectral rules file (URL-encoded if necessary)")] = Path(..., description="Path to the Spectral rules file (URL-encoded if necessary)", examples=["rulesets/basic-ruleset.yml"]),
    request: Request = None,
) -> ValidationResponse:
    """Creates a new validation resource by running Spectral against the uploaded OpenAPI document using the specified ruleset from the given version."""
    if not BaseValidationApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseValidationApi.subclasses[0]().create_validation(version, ruleset, request)
