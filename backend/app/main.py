"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


settings = get_settings()

app = FastAPI(
    title="AI-Powered Portfolio Optimization System",
    description="Live yfinance market data, predictive analytics, and portfolio optimization API",
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://[a-zA-Z0-9-]+\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# WebSocket routes (real-time live price updates)
from app.api.ws_routes import router as ws_router

app.include_router(ws_router)


@app.get("/")
def root():
    return {
        "name": "FinOptima Portfolio Optimization System",
        "docs": "/docs",
        "health": "/api/health",
        "data_source": "yfinance",
    }
