"""
Kairos API — FastAPI application entry point.

Run locally:
    cd backend
    source venv/bin/activate    (Windows/WSL2: same command inside Ubuntu)
    uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

import ee
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Google Earth Engine once at startup."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to backend/.env "
            "and fill in your GCP project ID."
        )
    try:
        ee_creds = os.getenv("EE_CREDENTIALS")
        if ee_creds:
            import json
            creds_path = os.path.expanduser("~/.config/earthengine/credentials")
            os.makedirs(os.path.dirname(creds_path), exist_ok=True)
            with open(creds_path, "w") as f:
                f.write(ee_creds)
        ee.Initialize(project=project_id)
        print(f"[kairos] Google Earth Engine initialized — project: {project_id}")
    except Exception as e:
        print(f"[kairos] GEE initialization FAILED: {e}")
        print("[kairos] Run: earthengine authenticate")
        raise
    yield

app = FastAPI(
    title="Kairos API",
    description="SAR satellite analysis platform — Sentinel-1 powered Earth observation.",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:4173",   # Vite preview build
    "https://kairos-mu-liart.vercel.app",
]
# Production frontend origin, set via env when deployed
prod_origin = os.getenv("FRONTEND_ORIGIN")
if prod_origin:
    allowed_origins.append(prod_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.analyze import router as analyze_router  # noqa: E402
from api.query import router as query_router      # noqa: E402
from api.scenes import router as scenes_router    # noqa: E402
from api.registry import router as registry_router  # noqa: E402
from api.status import router as status_router    # noqa: E402
from api.research import router as research_router  # noqa: E402
from api.exports import router as exports_router  # noqa: E402
from api.impact import router as impact_router  # noqa: E402

app.include_router(analyze_router)
app.include_router(query_router)
app.include_router(scenes_router)
app.include_router(registry_router)
app.include_router(status_router)
app.include_router(research_router)
app.include_router(exports_router)
app.include_router(impact_router)


@app.get("/health")
def health():
    """Liveness check — used by Cloud Run and the frontend connection badge."""
    return {"status": "ok", "service": "kairos-api", "version": "0.1.0"}
