from fastapi import FastAPI, Request, requests
from fastapi.exceptions import HTTPException
from routers import routes
from auth.auth import retrieve_token
from config import settings
from fastapi_utils.tasks import repeat_every
from sync.routes import sync_routes

app = FastAPI(title="GWA Kubernetes API",
              description="Description: API to create resources in Openshift using Kubectl",
              version="1.0.0")
app.include_router(routes.router)


@app.post("/token")
def login(request: Request):
    if "authorization" not in request.headers:
        raise HTTPException(status_code=400, detail="Invalid request")
    return retrieve_token(request.headers['authorization'],
                          settings.resourceAuthServer['serverUrl'] +
                          "realms/%s/protocol/openid-connect" % settings.resourceAuthServer['realm'],
                          'openid')


@app.get("/health")
def check_health():
    return "up"


@app.on_event("startup")
@repeat_every(seconds=int(settings.syncConfig["interval"]))
def init_jobs():
    sync_routes()
