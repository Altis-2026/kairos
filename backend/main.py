"""
Kairos API — FastAPI application entry point.

Run locally:
    cd backend
    source venv/bin/activate    (Windows/WSL2: same command inside Ubuntu)
    uvicorn main:app --reload --port 8000
"""

import os
import threading
from contextlib import asynccontextmanager

import ee
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import gee_ready

load_dotenv()


def _init_gee_in_background(project_id: str, ee_creds: str | None) -> None:
    """
    Runs off the FastAPI startup path (see lifespan below) so a Cloud Run
    cold start opens the port and answers /health immediately instead of
    blocking on this network call to Google's servers. gee_ready.wait()
    is the handshake any GEE-touching code path uses to wait for this to
    finish, without holding up unrelated routes.
    """
    try:
        if ee_creds:
            creds_path = os.path.expanduser("~/.config/earthengine/credentials")
            os.makedirs(os.path.dirname(creds_path), exist_ok=True)
            with open(creds_path, "w") as f:
                f.write(ee_creds)
        ee.Initialize(project=project_id)
        print(f"[kairos] Google Earth Engine initialized — project: {project_id}")
    except Exception as e:
        gee_ready.error = str(e)
        print(f"[kairos] GEE initialization FAILED: {e}")
        print("[kairos] Run: earthengine authenticate")
    finally:
        gee_ready.ready.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Kick off Earth Engine init in the background; don't block startup on it."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to backend/.env "
            "and fill in your GCP project ID."
        )
    threading.Thread(
        target=_init_gee_in_background,
        args=(project_id, os.getenv("EE_CREDENTIALS")),
        daemon=True,
    ).start()

    # Autonomous sweep: on a schedule, run analyses over active disaster zones
    # (NASA EONET) and a global watchlist, and store noteworthy findings for
    # the public /feed. Disable with FEED_SWEEP_ENABLED=0.
    from watch import store as feed_store
    from watch import sweeper as feed_sweeper

    feed_store.init_db()
    feed_sweeper.start_scheduler()

    # Janus mentor project memory (SQLite; see backend/janus/store.py) and
    # the proactive monitoring scheduler (opt-in via JANUS_WATCH_ENABLED).
    from janus import store as janus_store
    from janus import proactive as janus_proactive

    janus_store.init_db()
    janus_proactive.start_scheduler()
    yield

app = FastAPI(
    title="Kairos API",
    description="SAR satellite analysis platform — Sentinel-1 powered Earth observation.",
    version="0.1.0",
    lifespan=lifespan,
)

def _normalize_origin(origin: str) -> str:
    """CORS origin matching is exact; strip trailing slashes for consistency."""
    return origin.strip().rstrip("/")


allowed_origins = [
    _normalize_origin("http://localhost:5173"),   # Vite dev server
    _normalize_origin("http://localhost:4173"),   # Vite preview build
    _normalize_origin("https://openkairos.vercel.app"),
]
# Production frontend origin, set via env when deployed
prod_origin = os.getenv("FRONTEND_ORIGIN")
if prod_origin:
    allowed_origins.append(_normalize_origin(prod_origin))

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
from api.events import router as events_router  # noqa: E402
from api.alerts import router as alerts_router  # noqa: E402
from api.interpret import router as interpret_router  # noqa: E402
from api.feed import router as feed_router  # noqa: E402
from api.validation import router as validation_router  # noqa: E402
from api.waitlist import router as waitlist_router  # noqa: E402
from api.janus import router as janus_router  # noqa: E402
from api.keys import router as keys_router  # noqa: E402
from api.portfolio import router as portfolio_router  # noqa: E402

app.include_router(analyze_router)
app.include_router(query_router)
app.include_router(scenes_router)
app.include_router(registry_router)
app.include_router(status_router)
app.include_router(research_router)
app.include_router(exports_router)
app.include_router(impact_router)
app.include_router(events_router)
app.include_router(alerts_router)
app.include_router(interpret_router)
app.include_router(feed_router)
app.include_router(validation_router)
app.include_router(waitlist_router)
app.include_router(janus_router)
app.include_router(keys_router)
app.include_router(portfolio_router)


@app.middleware("http")
async def api_key_metering(request, call_next):
    """
    Programmatic access metering: when a request carries X-API-Key, resolve it
    to an owner and log the call. Purely additive today (identity + usage for
    future quotas); unauthenticated requests pass through untouched.
    """
    key = request.headers.get("x-api-key")
    if key:
        import apikeys

        owner = apikeys.resolve(key)
        if owner:
            apikeys.log_usage(owner, request.url.path)
    return await call_next(request)


@app.get("/health")
def health():
    """Liveness check — used by Cloud Run and the frontend connection badge."""
    return {"status": "ok", "service": "kairos-api", "version": "0.1.0"}
