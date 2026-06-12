"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import get_settings
#from app.utils.sample_data_generator import ensure_sample_data
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Navigate up to the workspace root to find the scripts folder
        root_dir = Path(__file__).resolve().parents[2] 
        script_path = root_dir / "scripts" / "generate_sample_data.py"
        
        if script_path.exists():
            print(f" Launcher: Running dataset preload script at {script_path}...")
            # Executes the script using the current active Python environment
            subprocess.run([sys.executable, str(script_path)], check=True)
            print(" Launcher: Dataset preloaded successfully.")
        else:
            print(f" Warning: Preload script not found at {script_path}")
    except Exception as e:
        print(f" Error: Failed to run startup script: {str(e)}")
    yield


settings = get_settings()

app = FastAPI(
    title="AI-Powered Portfolio Optimization System",
    description="Live market data, predictive analytics, and portfolio optimization API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "AI-Powered Portfolio Optimization System",
        "docs": "/docs",
        "health": "/api/health",
    }

raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
cors_origins = [origin.strip() for origin in raw_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
