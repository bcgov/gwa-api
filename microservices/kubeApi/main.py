from fastapi import FastAPI, Request, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from starlette.responses import HTMLResponse
from routers import routes
from auth.auth import retrieve_token, validate_permissions
from config import settings
from logger.log_config import CustomizeLogger


def create_app() -> FastAPI:
    app = FastAPI(title="GWA Kubernetes API",
                  description="Description: API to create resources in Openshift using Kubectl",
                  version="1.0.0")
    app.include_router(routes.router)

    logger = CustomizeLogger.make_logger(settings.logLevel)
    app.logger = logger

    return app


app = create_app()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


@app.post("/token")
def login(request: Request):
    if "authorization" not in request.headers:
        raise HTTPException(status_code=400, detail="Invalid request")
    return retrieve_token(request.headers['authorization'],
                          settings.resourceAuthServer['serverUrl'] +
                          "realms/%s/protocol/openid-connect" % settings.resourceAuthServer['realm'],
                          'openid')


@app.get("/health")
async def get_health():
    return {"status": "up"}


@app.get("/")
def main():
    title = """
    <h1>
        GWA KUBE API
    </h1>                                                                              """
    return HTMLResponse(title)
