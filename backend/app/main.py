"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.utils.sample_data_generator import ensure_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_sample_data()
    yield


settings = get_settings()

app = FastAPI(
    title="AI-Powered Portfolio Optimization System",
    description="Live market data, predictive analytics, and portfolio optimization API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "AI-Powered Portfolio Optimization System",
        "docs": "/docs",
        "health": "/api/health",
    }
