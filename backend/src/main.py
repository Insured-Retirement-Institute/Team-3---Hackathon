from pathlib import Path
import logging
from dotenv import load_dotenv

# Always load .env from the backend directory (so it works no matter where uvicorn is started)
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")

# Show logs for payload building (direct vs Bedrock) and carrier API calls
logging.basicConfig(level=logging.INFO)
for name in ("src.api.admin", "src.services.carrier_dispatcher", "src.services.carrier_transform_service"):
    logging.getLogger(name).setLevel(logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from src.api import admin, carrier, document, notifications
from src.utils.database import engine, Base
import os

use_json_store = os.getenv("USE_JSON_STORE", "true").lower() in {"1", "true", "yes"}
if not use_json_store:
    Base.metadata.create_all(bind=engine)

# Bearer token required in Authorization header for all /api/* requests. Override with AUTH_TOKEN env.
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJJUi1EZW1vIiwiZXhwIjoxOTk5OTk5OTk5fQ.dummy")

# Paths that do not require the auth header
NO_AUTH_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Require Authorization: Bearer <token> for all /api/* requests."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if path in NO_AUTH_PATHS or not path.startswith("/api"):
            return await call_next(request)
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header. Use: Authorization: Bearer <token>."},
            )
        token = auth[7:].strip()
        if token != AUTH_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "Invalid token."})
        return await call_next(request)


app = FastAPI(
    title="Advisor Onboarding API",
    description="API for broker/dealer advisor onboarding and carrier integration",
    version="1.0.0",
    swagger_ui_init_oauth=None,
)

# Apply Bearer auth first (outer), then CORS
app.add_middleware(BearerAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(carrier.router, prefix="/api/carrier", tags=["Carrier"])
app.include_router(document.router, prefix="/api", tags=["Document Extraction"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])

@app.get("/")
async def root():
    return {
        "message": "Advisor Onboarding API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Bearer token. Set AUTH_TOKEN in env to match the value sent by clients.",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi