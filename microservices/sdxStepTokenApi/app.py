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
from models import HealthResponse

logger = logging.getLogger(__name__)

_VALID_LOCATIONS = {"body", "query", "header", "path", "cookie"}

_OPENAPI_PATH_SUMMARIES = {
    "/tokens": "Step CA token management",
    "/health": "Health check endpoint",
}

# Injected in enrich_openapi_schema: FastAPI's schema pipeline sorts dict keys inside
# json_schema_extra, so examples are applied here to preserve field order.
_OPENAPI_COMPONENT_EXAMPLES = {
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


def _request_location(loc: tuple) -> str:
    """Return the request section from a Pydantic error loc tuple."""
    if not loc:
        return "body"
    first = loc[0]
    if not isinstance(first, str):
        return "body"
    if first not in _VALID_LOCATIONS:
        return "body"
    return first


def _pydantic_error_item(error: dict) -> dict:
    """Build one Problem Details error object from a Pydantic validation error dict."""
    item = {
        "type": "ValidationError",
        "location": _request_location(error["loc"]),
        "code": error["type"],
        "message": error["msg"],
    }
    if "input" in error:
        item["input"] = jsonable_encoder(error["input"])
    if "ctx" in error:
        item["ctx"] = error["ctx"]
    return item


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "type": "https://tools.ietf.org/html/rfc9110#section-15.5.21",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request body failed validation.",
            "errors": [_pydantic_error_item(e) for e in exc.errors()],
        },
    )


async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")


def _apply_path_summaries(schema: dict) -> None:
    paths = schema.get("paths") or {}
    for path, summary in _OPENAPI_PATH_SUMMARIES.items():
        if path in paths:
            paths[path]["summary"] = summary


def _apply_component_examples(schema: dict) -> None:
    schemas = (schema.get("components") or {}).get("schemas") or {}
    for name, examples in _OPENAPI_COMPONENT_EXAMPLES.items():
        if name in schemas:
            schemas[name]["examples"] = examples


def _enrich_openapi_schema(schema: dict) -> None:
    _apply_path_summaries(schema)
    _apply_component_examples(schema)


def _make_openapi_fn(app: FastAPI):
    def openapi():
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
        _enrich_openapi_schema(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    return openapi


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
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_api_route(
        "/health",
        get_health,
        methods=["GET"],
        operation_id="getHealth",
        summary="Get Health",
        description="Returns the health and readiness status of the service.",
        response_model=HealthResponse,
        responses={200: {"description": "Service is healthy and ready."}},
    )
    app.openapi = _make_openapi_fn(app)

    return app
