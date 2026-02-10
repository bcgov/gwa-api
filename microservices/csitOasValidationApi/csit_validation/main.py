from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from csit_validation.apis.root_api import router as RootApiRouter
from csit_validation.apis.discovery_api import router as DiscoveryApiRouter
from csit_validation.apis.validation_api import router as ValidationApiRouter

tags_metadata = [
    {
      "name": "Discovery",
      "description": "Browse available ruleset versions and files"
    },
    {
      "name": "Validation",
      "description": "Perform validation of OpenAPI documents"
    },
]

app = FastAPI(
    title="OAS Spectral Validation API",
    description=(
        "A governance API for discovering and using BCGov Spectral rulesets "
        "to validate OpenAPI Specification documents.\n"
        "Repository: https://github.com/bcgov/csit-api-governance-spectral-style-guide"
    ),
    version="0.1.0",
    openapi_tags=tags_metadata
)

app.include_router(RootApiRouter)
app.include_router(DiscoveryApiRouter)
app.include_router(ValidationApiRouter)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    # Generate the full default OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,      
        servers=app.servers,    
        terms_of_service=app.terms_of_service, 
        contact=app.contact,              
        license_info=app.license_info,  
    )

    # Remove internal/operational endpoints from public API spec
    # Health endpoints are not exposed and are for internal use only
    # Root endpoint is just a redirect to /docs
    internal_paths = ["/", "/livez", "/readyz", "/health"]
    for path in internal_paths:
        openapi_schema.get("paths", {}).pop(path, None)

    # Remove any response entries that have "x-remove": true
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "responses" in operation:
                responses = operation["responses"]
                # Collect status codes to remove
                codes_to_remove = [
                    code for code, resp in responses.items()
                    if isinstance(resp, dict) and resp.get("x-remove", False)
                ]
                # Remove them
                for code in codes_to_remove:
                    del responses[code]

    # Optional: clean up unused validation schemas if they are no longer referenced
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)
    
    # Remove HealthResponse schema if health endpoint is removed
    # (only remove if not used elsewhere)
    if "/health" in internal_paths:
        schemas.pop("HealthResponse", None)
        schemas.pop("HealthStatus", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
