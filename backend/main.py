import json
import os
import threading
from contextlib import asynccontextmanager

import ee
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

import gee_ready

load_dotenv()

EE_DEADLINE_MS = int(os.getenv("EE_DEADLINE_MS", "120000"))


def _init_gee_in_background(project_id: str, ee_creds: str | None) -> None:
    try:
        if ee_creds:
            info = json.loads(ee_creds)
            if info.get("type") == "service_account":
                ee.Initialize(
                    credentials=ee.ServiceAccountCredentials(info["client_email"], key_data=ee_creds),
                    project=project_id,
                )
            else:
                creds_path = os.path.expanduser("~/.config/earthengine/credentials")
                os.makedirs(os.path.dirname(creds_path), exist_ok=True)
                with open(creds_path, "w") as f:
                    f.write(ee_creds)
                ee.Initialize(project=project_id)
        else:
            ee.Initialize(project=project_id)
        ee.data.setDeadline(EE_DEADLINE_MS)
        print(f"[kairos] Earth Engine ready, project {project_id}")
    except Exception as e:
        gee_ready.error = str(e)
        print(f"[kairos] Earth Engine failed to initialize: {e}")
        print("[kairos] Run: earthengine authenticate")
    finally:
        gee_ready.ready.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to backend/.env "
            "and fill in your Google Cloud project ID."
        )
    threading.Thread(
        target=_init_gee_in_background,
        args=(project_id, os.getenv("EE_CREDENTIALS")),
        daemon=True,
    ).start()

    import featured
    from janus import proactive as janus_proactive
    from janus import store as janus_store
    from watch import store as feed_store
    from watch import sweeper as feed_sweeper

    feed_store.init_db()
    feed_sweeper.start_scheduler()
    janus_store.init_db()
    janus_proactive.start_scheduler()
    featured.start_warmer()
    yield


app = FastAPI(
    title="Kairos API",
    description="Satellite radar analysis for everyone, built on Sentinel-1 and Google Earth Engine.",
    version="1.0.0",
    lifespan=lifespan,
)


def _normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


allowed_origins = [
    "http://localhost:5173",
    "http://localhost:4173",
    "https://openkairos.vercel.app",
]
if os.getenv("FRONTEND_ORIGIN"):
    allowed_origins.extend(
        _normalize_origin(o) for o in os.environ["FRONTEND_ORIGIN"].split(",") if o.strip()
    )

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api import (  # noqa: E402
    agent,
    alerts,
    analyze,
    districts,
    events,
    exports,
    feed,
    foresight,
    impact,
    insar,
    interpret,
    janus,
    keys,
    myplace,
    portfolio,
    query,
    registry,
    research,
    scenes,
    simulate,
    status,
    validation,
    vessels,
)
from api import (
    featured as featured_api,
)

for module in (
    analyze,
    query,
    scenes,
    registry,
    status,
    research,
    exports,
    impact,
    events,
    alerts,
    interpret,
    feed,
    featured_api,
    validation,
    janus,
    keys,
    portfolio,
    foresight,
    vessels,
    insar,
    myplace,
    simulate,
    districts,
    agent,
):
    app.include_router(module.router)


@app.middleware("http")
async def api_key_metering(request, call_next):
    key = request.headers.get("x-api-key")
    if key:
        import apikeys

        owner = apikeys.resolve(key)
        if owner:
            apikeys.log_usage(owner, request.url.path)
    return await call_next(request)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "kairos-api",
        "version": "1.0.0",
        "earth_engine": "ready"
        if gee_ready.ready.is_set() and not gee_ready.error
        else ("starting" if not gee_ready.ready.is_set() else "unavailable"),
        "ai": "configured" if os.getenv("OPENROUTER_API_KEY") else "not configured",
    }
