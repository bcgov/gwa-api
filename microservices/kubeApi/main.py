from fastapi import FastAPI, Request, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from starlette.responses import HTMLResponse
from routers import routes
from config import settings
import logging
import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s - %(name)s] %(levelname)5s %(module)s.%(funcName)5s: %(message)s',
    }},
    'handlers': {'console': {
        'level': settings.log_level,
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'loggers': {
        'uvicorn': {
            'propagate': True
        },
        'fastapi': {
            'propagate': True
        }
    },
    'root': {
        'level': settings.log_level,
        'handlers': ['console']
    }
})

app = FastAPI(title="GWA Kubernetes API",
              description="Description: API to create resources in Openshift using Kubectl",
              version="1.0.0")
app.include_router(routes.router)

logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


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
