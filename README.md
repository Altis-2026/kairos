<div align="center">

<img src="frontend/public/kairos-icon.png" alt="Kairos" width="88" />

# Kairos

**Free satellite radar for everyone.**

Ask a question about any place on Earth and get a real measurement from space,
then simulate what could happen next and learn how to prepare.

[Live app](https://openkairos.vercel.app) · [API](docs/API.md) · [Science](docs/SCIENCE.md) · [Janus](docs/JANUS.md) · [Deployment](docs/DEPLOYMENT.md)

![CI](https://github.com/Altis-2026/kairos/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-00BFA8)

Built by **Prem Kamasani** and **Amogh Vinaykumar**, Flower Mound High School, Texas.

</div>

---

## Why Kairos exists

In July 2025 the Guadalupe River rose about 26 feet in under an hour and more
than 135 people died in the Texas Hill Country floods. The storm that caused the
flooding also hid it from camera satellites. Radar satellites see straight
through cloud, smoke and darkness, and Europe's Sentinel-1 mission images the
whole planet every few days for free. Almost nobody outside a research lab can
use that data, because it arrives as gigabyte files that need specialist
software and training.

Kairos removes that barrier. Type or say *"was there flooding near Kerrville in
July 2025?"* and about thirty seconds later the flood extent is on a 3D globe,
with the area in km², a confidence score and a plain explanation of what the
radar saw.

## What you can do

Kairos is organized around four jobs.

### Observe
- **Ask in plain language**, typed or spoken, in English or Spanish. Follow-up
  questions keep their context, one question can run several analyses, and a
  "why this analysis" toggle shows how the question was interpreted.
- **26 analyses** from one registry, including flood extent and depth, ship
  detection, wildfire burn scars, radar plus thermal fire fusion, oil spills,
  deforestation, sea ice and ice drift, earthquake building damage, land
  subsidence, urban growth, crop vigour, soil moisture, ocean wind, methane and
  air quality. The full list is in [docs/SCIENCE.md](docs/SCIENCE.md).
- **A guided wizard** for full control: pick a task, draw a rectangle or trace any
  shape, set dates, preview which radar passes exist, run, and read the result.
- **Live Watch**, a public map of active disasters from NASA EONET, plus an
  autonomous sweeper that analyzes active events on its own every few hours.

### Simulate
- **Flood simulation** with a local-inertial shallow-water solver on real
  Copernicus GLO-30 terrain.
- **Wildfire simulation** with the Rothermel surface spread model solved as a
  minimum-travel-time problem across real slope and fuel.
- **A custom WebGL2 3D view** that renders both over the terrain, with a time
  scrubber. Every simulated result is labelled as a simulation, never as an
  observation.

### Prepare
- **My Place**: enter any address and get recent flooding, fire damage, new
  construction and sinking ground around it, each in one sentence.
- **Foresight**: decades of satellite record turned into flood, wildfire, drought
  and subsidence exposure scores, seasonal peaks, Mann-Kendall and OLS trend
  tests, and a preparedness checklist.
- **My District**: load the real boundary of any US congressional district from
  the Census Bureau, run standing checks inside it, simulate a flood or wildfire
  nearby, and print a one-page situation briefing.

### Learn
- **Academy**: five short lessons on how radar sees the Earth, three narrated real
  cases you can rerun yourself, and a quiz.
- **Janus**, a research mentor that runs real analyses mid-conversation, searches
  the literature, validates results against ground truth and exports to LaTeX,
  BibTeX, notebooks and policy briefs.
- **Featured stories**: six real disasters that load straight onto the globe.

### The Lab
Research tools for going deeper: raw backscatter, optical comparison, before and
after swipe, time series with trend statistics, measured accuracy against
independent reference maps, confounder checks against real rainfall, wind and
land cover, batch CSV runs, area alerts, dark-vessel screening against AIS
broadcasts, and published InSAR interferograms.

Everything works without an account. Signing in with Google adds saved analyses
and alerts. Kairos also installs as an app from the browser.

## How a question becomes a map

```
 "was there flooding near Kerrville in July 2025?"
                     │
                     ▼
 Language model ───────────► analysis type, place, dates
 (via OpenRouter)
                     │
                     ▼
 Google Earth Engine ──────► filter Sentinel-1, calibrate, compare
                              against a baseline, isolate the change
                     │        (nothing is downloaded)
                     ▼
 FastAPI ──────────────────► tile URL + statistics + signed provenance
                     │
                     ▼
 React + Mapbox GL globe ──► overlay, headline number, confidence,
                              plain-language explanation
```

The physics in one paragraph: the satellite sends a microwave pulse and records
how much energy bounces back. Smooth water reflects the pulse away like a mirror,
so new flooding shows up as land that suddenly went dark. Buildings and ship
hulls bounce energy straight back, so they appear bright. Burned vegetation,
cleared forest and wet soil each change the echo in their own way. Every analysis
in Kairos is a different way of reading what changed in that echo.

## Accuracy and honesty

- Every number comes from deterministic computation on real satellite data, or
  from the physics models. The language model never produces a measurement.
- Results carry a confidence score, an uncertainty range from an ensemble of
  thresholds, and optical confirmation where a cloud-free Sentinel-2 scene exists.
- The Lab re-runs the production detectors over historical disasters and
  computes IoU, precision, recall and F1 against the Global Flood Database,
  MODIS burned area and Hansen forest change.
- Every result is signed with an HMAC provenance stamp, and `POST /verify`
  confirms it has not been altered.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Zustand, TanStack Query |
| Map and 3D | Mapbox GL JS globe, custom WebGL2 terrain and water renderer |
| Backend | Python 3.11, FastAPI, Pydantic |
| Satellite processing | Google Earth Engine (Sentinel-1, Sentinel-2, Sentinel-5P, Landsat, ALOS PALSAR, GLO-30) |
| Physics | NumPy flood and wildfire solvers |
| Language | A hosted language model through OpenRouter |
| Accounts | Firebase Auth and Firestore (optional) |
| Hosting | Vercel (frontend), Google Cloud Run (backend) |
| Quality | pytest (300+ tests), Vitest, ESLint, Ruff, GitHub Actions CI |

## Run it locally

You need Python 3.11+, Node 20+, a free [Google Earth Engine](https://earthengine.google.com/)
registration tied to a Google Cloud project, a free Mapbox token, and an
[OpenRouter](https://openrouter.ai) key for the chat. On Windows, use WSL2.

**Backend**

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set GOOGLE_CLOUD_PROJECT and OPENROUTER_API_KEY
earthengine authenticate        # one-time browser login
python test_gee.py              # prints an image count if Earth Engine works
uvicorn main:app --reload --port 8000
```

**Frontend**, in a second terminal

```bash
cd frontend
npm install
cp .env.example .env            # set VITE_MAPBOX_TOKEN
npm run dev                     # http://localhost:5173
```

Open the app, press **Launch Kairos**, and try a featured story or ask a question.
The wizard, featured stories, simulations and map tools work without the
OpenRouter key; only the chat, explanations and Janus need it.

**Tests**

```bash
cd backend && pip install -r requirements-dev.txt && ruff check . && pytest
cd frontend && npm run typecheck && npm run lint && npm test
```

The backend suite needs no credentials or network: Earth Engine calls and terrain
fetches are stubbed, and the solver tests run on synthetic terrain.

## Project structure

```
kairos/
├── backend/
│   ├── main.py            app entry, Earth Engine startup, routers
│   ├── api/               one router per feature (analyze, query, districts,
│   │                      featured, simulate, foresight, janus, ...)
│   ├── gee/               every analysis plus the registry
│   ├── solver/            flood and wildfire physics, with tests
│   ├── janus/             the research mentor: tools, memory, exports
│   ├── watch/             autonomous disaster sweeper
│   ├── ai/                language model client, parser, system prompt
│   ├── ratelimit.py       free-tier limits per visitor
│   ├── result_cache.py    repeat answers without recomputing
│   └── tests/
├── frontend/src/
│   ├── components/        globe, chat, panels, landing, academy, 3D view
│   ├── stores/            Zustand state
│   ├── api/               typed client, one module per endpoint group
│   ├── lib/               chat, navigation, voice, i18n, geometry, exports
│   └── test/
└── docs/
```

## Adding an analysis

1. Write `backend/gee/your_analysis.py` with the shared signature: `bbox`,
   `start_date` and `end_date` in, a dict with `tile_url` and `data_date` out.
2. Add one entry to `ANALYSIS_REGISTRY` in `backend/gee/registry.py`.
3. Add a row to `backend/ai/system_prompt.md` so the chat can choose it.

The wizard, the API and Janus pick it up automatically.

## AI disclosure

**In the product.** Claude Haiku 4.5, accessed through OpenRouter, turns
questions into analysis parameters and writes plain-language explanations of
finished results. Claude Sonnet 4.6 powers Janus's study-design, peer-review
and autopilot modes. AI never produces a measurement, and the analyses,
simulations, featured stories and map tools all work without it.

**In development.** We used Claude (Anthropic) as an AI assistant while building
Kairos, for brainstorming features and as a coding assistant that wrote and
revised parts of the code under our direction. Commits it authored are labelled
in the git history.

## Data and credit

Contains modified Copernicus Sentinel data processed on Google Earth Engine.
Surface water and settlement layers from the European Commission Joint Research
Centre. Elevation from Copernicus GLO-30. Disaster events from NASA EONET.
Congressional districts from the US Census Bureau TIGERweb service. Vessel
broadcasts from NOAA and BOEM MarineCadastre. Reference maps from the Global
Flood Database, MODIS and Hansen Global Forest Change. Basemaps by Mapbox.
Open-source libraries are listed in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## License

MIT. See [LICENSE](LICENSE).
