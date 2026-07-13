import os
from contextlib import asynccontextmanager

import ee
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to backend/.env "
            "and fill in your GCP project ID."
        )
    try:
        ee_creds = os.getenv("EE_CREDENTIALS")
        print(f"[kairos] build check v2 | EE_CREDENTIALS present: {bool(ee_creds)}, length: {len(ee_creds) if ee_creds else 0}")
        if ee_creds:
            import json
            key_dict = json.loads(ee_creds)
            print(f"[kairos] service account email: {key_dict.get('client_email')}")
            credentials = ee.ServiceAccountCredentials(
                key_dict["client_email"], key_data=ee_creds
            )
            ee.Initialize(credentials, project=project_id)
        else:
            ee.Initialize(project=project_id)
        print(f"[kairos] Google Earth Engine initialized, project: {project_id}")
    except Exception as e:
        print(f"[kairos] GEE initialization FAILED: {e}")
        print("[kairos] Run: earthengine authenticate")
        raise

    from watch import store as feed_store
    from watch import sweeper as feed_sweeper

    feed_store.init_db()
    feed_sweeper.start_scheduler()
    yield

app = FastAPI(
    title="Kairos API",
    description="SAR satellite analysis platform running on Sentinel-1 radar data.",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:4173",
    "https://kairos-mu-liart.vercel.app",
]
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

from api.analyze import router as analyze_router
from api.query import router as query_router
from api.scenes import router as scenes_router
from api.registry import router as registry_router
from api.status import router as status_router
from api.research import router as research_router
from api.exports import router as exports_router
from api.impact import router as impact_router
from api.events import router as events_router
from api.alerts import router as alerts_router
from api.interpret import router as interpret_router
from api.feed import router as feed_router
from api.districts import router as districts_router

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
app.include_router(districts_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kairos-api", "version": "0.1.0"}
