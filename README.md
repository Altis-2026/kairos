<div align="center">

# Kairos

**Ask the Earth a question. Get a radar answer.**

Sentinel-1 SAR analysis, an AI research mentor, and hazard exposure outlooks — all running live on a 3D globe, free ESA data, zero raster downloads.

[Live app](https://openkairos.vercel.app) · [API reference](docs/API.md) · [Janus docs](docs/JANUS.md)

</div>

---

## What this is

Type something like *"is there flooding near Dhaka right now?"* and Kairos turns it into a real satellite radar analysis: a natural-language model resolves the place, hazard, and date window; Google Earth Engine processes the actual Sentinel-1 scenes entirely server-side; and the result — a coloured overlay, a headline number, a confidence score, and a plain-language explanation — lands on a 3D globe in seconds.

Radar sees through cloud, smoke, and darkness, and Sentinel-1 covers the whole planet every 12 days for free. Nothing is ever downloaded — Kairos never touches a raw scene locally; every computation runs inside Earth Engine and only a rendered tile layer and a stats dictionary come back.

## Highlights

**22 SAR & optical analyses**, one registry, zero hardcoding — flood extent and depth, ship detection, wildfire burn scars, oil spills, deforestation, sea ice extent *and* drift, land subsidence, building damage, urban growth, crop vigour, illegal land disturbance, forest biomass, methane, air quality, soil moisture, flooded forest, wet snow, SAR+optical flood consensus, and L-band archaeology mode.

**Janus** — an AI research mentor, not a chatbot. Four modes (mentor, study design, adversarial peer review, autopilot), 20+ callable tools that run real analyses mid-conversation, live literature search, ground-truth validation, confounder screening, hypothesis tracking, and exports to LaTeX, BibTeX/RIS, runnable Python notebooks, policy briefs, and publication-ready figures.

**Foresight** — hazard exposure outlooks for any place on Earth, built from decades of measured satellite record rather than a black-box forecast: flood, wildfire, drought, and subsidence, each with a 0–100 score, a seasonal profile, a statistically rigorous trend test, and — for flood — a live self-reported accuracy check against an independent reference dataset.

**Maritime domain awareness** — dark-vessel screening fuses radar ship detections with real AIS transponder broadcasts to flag returns with no matching transponder, caveats included.

**Also inside**: a public Live Watch disaster feed, Guardian citizen-science vetting for illegal mining/clearing, an InSAR deep-dive panel with published interferograms, batch CSV analysis, embeddable result widgets, a cryptographically signed provenance system, a public accuracy scoreboard, portfolio monitoring for many sites at once, and a full offline-capable PWA.

## Architecture

```
Natural language query
        │
        ▼
  OpenRouter (Claude Haiku 4.5 / Sonnet 4.6)   →  structured analysis parameters
        │
        ▼
  Google Earth Engine                          →  server-side Sentinel-1 processing
        │                                          (nothing downloaded, ever)
        ▼
  FastAPI backend                              →  tile URL + stats dictionary
        │
        ▼
  React + Mapbox GL globe                      →  rendered overlay + explanation
```

## What's inside

```
kairos/
├── CLAUDE.md                  ← project conventions for Claude Code
├── docs/
│   ├── API.md                 ← full endpoint reference
│   ├── JANUS.md                ← Janus architecture & design
│   └── WEEK1_GUIDE.md         ← original setup walkthrough
├── backend/                   ← FastAPI + Earth Engine + OpenRouter
│   ├── main.py                ← app entry, GEE init, CORS, API-key metering
│   ├── api/                   ← one router per endpoint group (22 groups)
│   ├── gee/                   ← every analysis function + the registry
│   ├── janus/                 ← the research-mentor system (store, tools,
│   │                             mentor loop, curricula, exports, ...)
│   ├── watch/                 ← autonomous disaster-feed sweeper
│   ├── ai/                    ← OpenRouter client, NL parser, system prompt
│   ├── models/                ← Pydantic request/response schemas
│   ├── jobs/                  ← optional Redis queue + worker
│   ├── stats.py               ← dependency-free OLS + Mann-Kendall trend tests
│   ├── provenance.py          ← HMAC-signed result verification
│   ├── test_gee.py            ← run this first to prove GEE auth works
│   └── Dockerfile             ← Cloud Run deployment
└── frontend/                  ← React + Vite + TypeScript + Mapbox
    └── src/
        ├── components/        ← Globe, TopNav, Sidebar wizard, Chat, Janus,
        │                         Foresight, Watch, Guardian, Panels/, ...
        ├── stores/             ← Zustand: map, sidebar FSM, chat, auth
        ├── api/                ← typed client, one module per endpoint group
        └── lib/                ← voice, sharing, embedding, exports, ...
```

## Quickstart (local)

Prerequisites: Python 3.11+, Node 20+, a Google Earth Engine-registered GCP project, a Mapbox token, an [OpenRouter](https://openrouter.ai) API key. Windows users: run everything inside WSL2.

**Backend**

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in GOOGLE_CLOUD_PROJECT + OPENROUTER_API_KEY
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

Try: *"Is there flooding near Dhaka right now?"* — or open **Menu** for the guided six-step analysis wizard, **Foresight** for a hazard outlook on any address, or the Janus panel to talk to the research mentor.

## Adding a new analysis type

1. Write `gee/your_analysis.py`, following the exact signature every other analysis uses (`bbox`, `start_date`, `end_date` in; a dict with `tile_url` and `data_date` out).
2. Add one entry to `ANALYSIS_REGISTRY` in `gee/registry.py`.

Nothing else changes — the `/registry` endpoint, the sidebar wizard, and Janus's `run_analysis` tool all pick it up automatically.

## Sign-in (optional)

Google sign-in via Firebase Auth. Add the three `VITE_FIREBASE_*` values to `frontend/.env` to enable it; without them Kairos runs normally, with the sign-in button explaining how to turn it on.

## Deploying

`.github/workflows/deploy.yml` ships the backend to Cloud Run and the frontend to Firebase Hosting on every push to `main` (and can be triggered manually via `workflow_dispatch`). The repository secrets it needs are listed at the top of that file. The production frontend at [openkairos.vercel.app](https://openkairos.vercel.app) deploys independently via Vercel's own GitHub integration.

## Documentation

- [`docs/API.md`](docs/API.md) — every endpoint, request, and response shape
- [`docs/JANUS.md`](docs/JANUS.md) — the research-mentor system's architecture and design decisions
- [`docs/WEEK1_GUIDE.md`](docs/WEEK1_GUIDE.md) — the original from-scratch setup walkthrough

---

<div align="center">

Built by lead developer **Amogh Vinaykumar**.
Sentinel-1 data: ESA Copernicus, via Google Earth Engine.

</div>
