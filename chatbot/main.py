"""
Mentaura AI Service — FastAPI application entry point.
Run: uvicorn main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from api.rest import router as rest_router
from api.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Mentaura AI Service starting...")
    from models.loader import get_models
    get_models()
    print("✅ Startup complete")
    yield
    print("👋 Shutting down")


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


app.include_router(rest_router, prefix="/api", tags=["REST"])
app.include_router(ws_router, tags=["WebSocket"])
