from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from starlette.responses import HTMLResponse
from routers.routes import router

def create_app():
    app = FastAPI(title="GWA Compatibility API",
                description="API to validate Kong Gateway configuration files",
                version="1.0.0")

    app.include_router(router)

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
            GWA COMPATIBILITY API
        </h1>
        """
        return HTMLResponse(title)
    
    return app 