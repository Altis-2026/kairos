# Kairos — Claude Code Project Context

## What This Project Is

Kairos is a web-based SAR (Synthetic Aperture Radar) analysis platform. Users type natural language like "is there flooding near Dhaka right now?" and get real satellite data analysis results on a 3D interactive globe. It uses free Sentinel-1 radar data from ESA which covers the entire Earth every 12 days through clouds and at night. The backend is Python/FastAPI, the frontend is React/TypeScript/Mapbox, everything runs on Google Cloud.

The product is called Kairos, built by the Altis team. The benchmark to beat is NeoEarth by AxionOrbital.

---

## Stack

**Backend:** Python 3.11, FastAPI, Google Earth Engine Python API (earthengine-api), Anthropic API using claude-sonnet-4-6, Redis + rq for job queue, PostgreSQL + PostGIS  
**Frontend:** React 18, TypeScript, Vite, Mapbox GL JS, Zustand, TanStack Query, Tailwind CSS, Framer Motion  
**Infrastructure:** Google Cloud Run, Firebase Hosting, Firebase Auth, Google Cloud Storage

---

## Non-Negotiable Rules for GEE Code

These rules are critical. Breaking them causes errors that are hard to debug.

1. **NEVER download raw satellite data.** All computation happens server-side on Google Earth Engine. Never call `.download()`, never write rasters locally during analysis, never try to load SAR files from disk.

2. **Every GEE analysis function returns a tile URL** by calling `getMapId()` on the result image, plus a stats dictionary. The frontend uses the tile URL as a Mapbox raster source.

3. **Always filter Sentinel-1** with `.filter(ee.Filter.eq('instrumentMode', 'IW'))` and `.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))` (or VH where specified). Never use the raw collection without these filters.

4. **Always clip** the result image to the input geometry before calling `getMapId()`. Use `.clip(geometry)` at the end of your processing chain.

5. **Always use `bestEffort=True`** in `reduceRegion()` calls. Without it, large AOIs exceed GEE's memory limits and the call fails.

6. **The Sentinel-1 GRD collection name is:** `COPERNICUS/S1_GRD`

7. **Never make blocking GEE calls (`.getInfo()`) inside `async` FastAPI endpoints.** Use synchronous endpoints (`def` not `async def`) for anything that calls GEE.

---

## Exact Template for Every GEE Analysis Function

Every new analysis type must follow this exact signature and return shape. Do not deviate from this pattern:

```python
import ee
from datetime import datetime, timedelta

def analyze_TYPENAME(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date: 'YYYY-MM-DD'
        end_date: 'YYYY-MM-DD'
    Returns:
        dict containing at minimum: tile_url (str), data_date (str)
    Raises:
        ValueError: if no satellite data is available for the given bbox/dates
    """
    geometry = ee.Geometry.Rectangle(bbox)

    # ... GEE computation here ...

    result_image = result_image.clip(geometry)
    map_id_dict = result_image.getMapId({'palette': ['#00BFA8'], 'min': 0, 'max': 1})
    tile_url = map_id_dict['tile_fetcher'].url_format

    return {
        'tile_url': tile_url,
        'data_date': data_date,  # actual date string from the satellite imagery used
        # ... analysis-specific stats below ...
    }
```

---

## AnalysisRegistry Pattern

The registry in `gee/registry.py` is a Python dict mapping string IDs to config dicts. It is the single source of truth for all analysis metadata. When adding a new analysis type:

1. Create the GEE function file (e.g. `gee/ships.py`)
2. Add one entry to the registry in `gee/registry.py`
3. Nothing else needs to change

Example registry entry:
```python
"flood_extent": {
    "function": detect_flood,        # the callable to invoke
    "display_name": "Flood Extent Mapping",
    "description": "Detects surface water inundation using backscatter change detection.",
    "category": "Disaster Response",
    "data_sources": ["S1"],          # badges shown in the frontend sidebar
    "estimated_seconds": 15,
    "output_type": "raster",
    "color_palette": ["#00BFA8"],
    "icon": "waves"
}
```

---

## FastAPI Patterns

- All request and response types are Pydantic models in `models/requests.py` and `models/responses.py`
- All GEE functions go in `gee/`, one file per analysis type
- All endpoints go in `api/`, one file per endpoint group — each exports `router = APIRouter()`
- Always wrap GEE function calls in try/except. Catch `ValueError` (user-facing: no data available) separately from `Exception` (server error: GEE failed)
- Use `lifespan` context manager for startup/shutdown logic, not the deprecated `@app.on_event("startup")`
- Use `load_dotenv()` at the top of `main.py` before any env var reads

---

## Key GEE Collections

```
COPERNICUS/S1_GRD               Sentinel-1 SAR — the primary data source
JRC/GSW1_4/GlobalSurfaceWater   Permanent water mask (exclude from flood results)
COPERNICUS/DEM/GLO30            30m elevation model (flood depth estimation)
ESA/WorldCover/v200             Global land cover classification
USDA/NASS/CDL                   US-only crop type map
LANDSAT/LC09/C02/T1_L2          Landsat 9 optical imagery
```

---

## Design Colors — Use These Exactly

```
Background:     #0B120E   (near-black with green tint)
Accent:         #E8A318   (amber — buttons, CTAs, active states)
SAR results:    #00BFA8   (teal — all analysis overlays, data badges)
Surface:        #131A15   (slightly lighter than background — cards, panels)
Text primary:   #E8EFE9
Text secondary: #8A9E8C
```

---

## File Structure

```
backend/
  main.py                  FastAPI app, CORS, GEE init, router includes
  models/
    requests.py            Pydantic models for API requests
    responses.py           Pydantic models for API responses
  api/
    analyze.py             POST /analyze
    query.py               POST /query (AI natural language)
    scenes.py              GET /scenes
    registry.py            GET /registry
  gee/
    registry.py            ANALYSIS_REGISTRY dict — single source of truth
    flood.py               Flood extent detection
    ships.py               Ship detection
    fire.py                Wildfire burn scar
    oil.py                 Oil spill detection
    deforestation.py       Deforestation mapping
    ice.py                 Sea ice extent
  ai/
    client.py              Anthropic API client
    system_prompt.md       The Kairos Claude system prompt
    parser.py              Response parser and validator
  jobs/
    queue.py               Redis queue setup
    worker.py              Background job worker

frontend/
  src/
    App.tsx
    main.tsx
    stores/
      mapStore.ts          Globe state: center, zoom, layers, AOI geometry
      sidebarStore.ts      Sidebar state: step, analysis type, job, result
      chatStore.ts         Chat state: messages, loading
      authStore.ts         Auth state: user, token
    components/
      Globe.tsx            Pure renderer — reads from mapStore, never owns state
      Sidebar/
        Sidebar.tsx        Finite state machine — 6 steps, explicit transitions
        steps/
          SelectTask.tsx
          DefineAOI.tsx
          Configure.tsx
          PreviewScenes.tsx
          RunAnalysis.tsx
          ShowResult.tsx
      Chat/
        ChatBar.tsx
        ChatMessage.tsx
        SuggestionChips.tsx
      Panels/
        LayerPanel.tsx
        AnalyticsPanel.tsx
      TopNav.tsx
      RightToolbar.tsx
    api/
      analyze.ts
      query.ts
      scenes.ts
      registry.ts
    types/
      analysis.ts
      map.ts
```

---

## Current Build Status

Update this section as each week completes.

- [ ] Week 1: GEE authenticated, flood detection working, FastAPI /analyze running
- [ ] Week 2: Ship detection added, Claude /query endpoint working
- [ ] Week 3: React frontend with Mapbox globe, first SAR layer on the globe
- [ ] Week 4: Full 6-step sidebar wired end to end
- [ ] Week 5: Five analysis types, suggestion chips, dark theme polished
- [ ] Week 6: Six types, timeline slider, analytics panel, comparison mode
- [ ] Week 7: Exports, Firebase auth, history panel
- [ ] Week 8: Deployed to production, live at custom domain

---

## Example Prompts That Work Well

**Adding a new analysis type:**
"Write a ship detection GEE function in `gee/ships.py` following the exact same pattern as `gee/flood.py`. It should detect vessels using CFAR on the VV band — look for pixels that are anomalously brighter than the surrounding ocean. Return tile_url, vessel_count, and data_date."

**Updating the registry:**
"Add `ship_detection` to the ANALYSIS_REGISTRY in `gee/registry.py` with display_name='Ship Detection', category='Maritime and Security', data_sources=['S1'], estimated_seconds=20, icon='ship'."

**Fixing an endpoint:**
"The /analyze endpoint in `api/analyze.py` is returning 422 for this request body: [paste body]. Fix the Pydantic model in `models/requests.py` to accept it, and explain what the validation was rejecting."

**Adding a Pydantic model:**
"Write a Pydantic response model in `models/responses.py` for the flood analysis endpoint. Include tile_url (str), flood_area_km2 (float), confidence (float, 0-1), data_date (str, YYYY-MM-DD), and post_images_used (int)."

**Bad prompts — too vague:**
- "Add ship detection" — doesn't say where or which pattern to follow
- "Fix the backend" — too vague
- "Make it look better" — no specific target

---

## Key Decisions Already Made

- **All SAR analysis runs on GEE, not locally.** We never set up a local SNAP or QGIS processing pipeline.
- **The frontend Globe component is a pure renderer.** It never owns state — it reads from `mapStore` and renders accordingly.
- **The Sidebar is a finite state machine.** Six explicit states, explicit transition functions, no ambiguous state possible.
- **Redis queue for jobs over 5 seconds.** Synchronous for fast analyses, async job queue for slow ones.
- **Anthropic API uses claude-sonnet-4-6.** Not Haiku (too weak for structured JSON extraction) and not Opus (too expensive).
