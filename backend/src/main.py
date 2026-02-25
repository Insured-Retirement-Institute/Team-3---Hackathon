from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import admin, carrier, document
from src.utils.database import engine, Base
import os

use_json_store = os.getenv("USE_JSON_STORE", "true").lower() in {"1", "true", "yes"}
if not use_json_store:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advisor Onboarding API",
    description="API for broker/dealer advisor onboarding and carrier integration",
    version="1.0.0"
)

# CORS
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