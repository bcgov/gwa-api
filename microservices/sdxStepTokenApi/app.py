from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from config import settings
from clients.step import bootstrap
from routers.routes import router

logger = logging.getLogger(__name__)


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
        description="API to generate one-time tokens for Step CA",
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
            content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
        )

    @app.get("/health")
    async def get_health():
        return {"status": "ok"}

    return app
