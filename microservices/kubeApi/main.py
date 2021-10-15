from fastapi import FastAPI, Request, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.routers import routes
from app.auth.auth import retrieve_token
from app.config import settings
import logging
import logging.config
import os
import json
import logging


# Logging configuration
logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(asctime)s %(levelname)5s %(module)-15s: %(message)s',
    }},
    'handlers': {'console': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': settings.logLevel,
        'handlers': ['console']
    }
})
logger = logging.getLogger(__name__)

app = FastAPI(title="GWA Kubernetes API",
              description="Description: API to create resources in Openshift using Kubectl",
              version="1.0.0")
app.include_router(routes.router)


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


@app.get("/")
async def root():
    return {"status": "up"}
