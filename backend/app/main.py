"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from pathlib import Path
import subprocess  # 🚨 MAKE SURE THIS LINE IS PRESENT
import sys  
>>>>>>> bcd5b3b25b2163280337cc55f4974cbe508e48e8

#from app.utils.sample_data_generator import ensure_sample_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_dir = Path(__file__).resolve().parents[2] / "live_data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "daily").mkdir(parents=True, exist_ok=True)
    (cache_dir / "intraday").mkdir(parents=True, exist_ok=True)
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "FinOptima Portfolio Optimization System",
        "docs": "/docs",
        "health": "/api/health",
        "data_source": "yfinance",
    }
