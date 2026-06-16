# Kairos — SAR Earth Observation by Altis

Ask questions about Earth in plain language. Kairos parses your intent with Claude, runs Sentinel-1 radar analysis on Google Earth Engine (nothing is ever downloaded — petabytes stay in the cloud), and renders the answer as a glowing layer on a 3D globe with a plain-language explanation.

Radar sees through clouds, smoke, and darkness. Floods during storms, fires through smoke, ships at night.

## What's inside

```
kairos/
├── CLAUDE.md                  ← context file for Claude Code (keep at root)
├── backend/                   ← FastAPI + Google Earth Engine + Claude
│   ├── main.py                ← app entry, GEE init, CORS
│   ├── api/                   ← /analyze /query /scenes /registry /status
│   ├── gee/                   ← the analysis functions + registry
│   ├── ai/                    ← Claude client, parser, system prompt
│   ├── models/                ← Pydantic request/response schemas
│   ├── jobs/                  ← optional Redis queue + worker
│   ├── test_gee.py            ← run this first to prove GEE works
│   └── Dockerfile             ← Cloud Run deployment
└── frontend/                  ← React + Vite + TypeScript + Mapbox globe
    └── src/
        ├── components/        ← Globe, TopNav, Sidebar wizard, Chat, Panels
        ├── stores/            ← Zustand: map, sidebar FSM, chat, auth
        ├── api/               ← typed client for the backend
        └── lib/firebase.ts    ← Google sign-in (optional, guarded)
```

## Quickstart (local)

Prerequisites: Python 3.11+, Node 20+, a Google Earth Engine-registered GCP project, a Mapbox token, an Anthropic API key. Windows users: run everything inside WSL2.

**Backend**

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in GOOGLE_CLOUD_PROJECT + ANTHROPIC_API_KEY
earthengine authenticate        # one-time browser login
python test_gee.py              # should print an image count
uvicorn main:app --reload --port 8000
```

**Frontend** (second terminal)

```bash
cd frontend
npm install
cp .env.example .env            # fill in VITE_MAPBOX_TOKEN
npm run dev                     # → http://localhost:5173
```

Try: *"Is there flooding near Dhaka right now?"* — or open **Menu** for the guided analysis wizard.

## The six analyses (v1)

| Analysis | Physics | Output |
|---|---|---|
| Flood extent | Water kills VV backscatter (−3 dB vs baseline) | teal raster + km² |
| Ship detection | Hulls are corner reflectors (mean + 5σ) | points + count |
| Wildfire burn scar | Bare soil raises VH (+2.5 dB) | raster + km² |
| Oil spill | Slicks damp capillary waves (dark anomaly) | raster + km² |
| Deforestation | Canopy loss drops VH vs 12-month baseline | raster + km² |
| Sea ice | Ice is bright in polar EW/HH | raster + km² |

Add a new one: write `gee/your_analysis.py`, add one entry to `gee/registry.py`. The API and the sidebar pick it up automatically.

## Sign-in (optional)

Google sign-in via Firebase Auth. Add the three `VITE_FIREBASE_*` values to `frontend/.env` to enable it; without them Kairos runs normally with the button explaining how to turn it on.

## Deploying

`.github/workflows/deploy.yml` ships the backend to Cloud Run and the frontend to Firebase Hosting on push to `main`. The secrets it needs are listed at the top of that file.

---

Built by the Altis team. Sentinel-1 data: ESA Copernicus, via Google Earth Engine.
