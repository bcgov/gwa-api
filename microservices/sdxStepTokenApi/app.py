from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from config import settings
from clients.step import bootstrap
from routers.routes import router
from routers.models import HealthResponse

logger = logging.getLogger(__name__)

_VALID_LOCATIONS = {"body", "query", "header", "path", "cookie"}


def _request_location(loc: tuple) -> str:
    """Return the request section from a Pydantic error loc tuple."""
    if loc and isinstance(loc[0], str) and loc[0] in _VALID_LOCATIONS:
        return loc[0]
    return "body"


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap(
        ca_url=settings.step_ca_url,
        fingerprint=settings.step_ca_fingerprint,
    )
    yield


def create_app():
    app = FastAPI(
        title="SDX CA Token API",
        summary="One-time token generation for Step CA",
        description=(
            "Generates one-time-use tokens for the Step CA certificate authority, "
            "used by SDX services to obtain X.509 certificates."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "type": "https://tools.ietf.org/html/rfc9110#section-15.5.21",
                "title": "Validation Error",
                "status": 422,
                "detail": "Request body failed validation.",
                "errors": [
                    {
                        "type": "ValidationError",
                        "location": _request_location(e["loc"]),
                        "code": e["type"],
                        "message": e["msg"],
                        **({"input": jsonable_encoder(e["input"])} if "input" in e else {}),
                        **({"ctx": e["ctx"]} if "ctx" in e else {}),
                    }
                    for e in exc.errors()
                ],
            },
        )

    @app.get(
        "/health",
        operation_id="getHealth",
        summary="Get Health",
        description="Returns the health and readiness status of the service.",
        response_model=HealthResponse,
        responses={200: {"description": "Service is healthy and ready."}},
    )
    async def get_health() -> HealthResponse:
        return HealthResponse(status="ok")

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
        )

        # FastAPI does not support path item-level summaries via decorators;
        # inject them directly into the generated schema.
        path_summaries = {
            "/tokens": "Step CA token management",
            "/health": "Health check endpoint",
        }
        for path, path_summary in path_summaries.items():
            if path in schema.get("paths", {}):
                schema["paths"][path]["summary"] = path_summary

        # Inject schema examples here rather than via json_schema_extra on the
        # models, because FastAPI's schema pipeline sorts dict keys alphabetically
        # inside json_schema_extra values, breaking intentional field ordering.
        component_examples = {
            "TokenRequest": [
                {
                    "subject": "my-service.clients.sdx",
                    "san": ["alt-name-1.clients.sdx", "10.0.0.5"],
                }
            ],
            "TokenResponse": [
                {"token": "eyJhbGciOiJFUzI1NiJ9.payload.sig"}
            ],
            "HealthResponse": [
                {"status": "ok"}
            ],
            "HTTPValidationError": [
                {
                    "type": "https://tools.ietf.org/html/rfc9110#section-15.5.21",
                    "title": "Validation Error",
                    "status": 422,
                    "detail": "Request body failed validation.",
                    "errors": [
                        {
                            "type": "ValidationError",
                            "location": "body",
                            "code": "missing",
                            "message": "Field required",
                        }
                    ],
                }
            ],
            "ValidationError": [
                {
                    "type": "ValidationError",
                    "location": "body",
                    "code": "missing",
                    "message": "Field required",
                }
            ],
        }
        schemas = schema.get("components", {}).get("schemas", {})
        for name, examples in component_examples.items():
            if name in schemas:
                schemas[name]["examples"] = examples

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app
