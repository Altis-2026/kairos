# Kairos — Week 1 Complete Setup Guide
> Everything you need to go from zero to a working flood detection API.
> End goal: `curl localhost:8000/analyze` returns a real Mapbox tile URL backed by Sentinel-1 satellite data.

---

## What You Are Building This Week

By the end of Week 1 you will have two working things:

1. A Python script that asks Google Earth Engine "how many Sentinel-1 radar images exist over Bangladesh?" and prints a real number.
2. A FastAPI server running on your machine where you can send a location and date range and get back a tile URL you can drop straight into Mapbox to see real flood data.

Everything else in Kairos builds on top of these two things. Get these right and you have solid foundations.

---

## Before You Start: Operating System

These instructions are written for **macOS**. If you are on Linux, skip the Homebrew step — use your package manager instead (`apt`, `dnf`, etc.) and everything else is identical. If you are on Windows, install **WSL2** first (Windows Subsystem for Linux), open an Ubuntu terminal inside it, and follow the Linux path. Running Python and GEE natively on Windows without WSL2 causes pain — avoid it.

---

## Part 1 — Create All Your Accounts First

Do this before installing any software. Some accounts (GEE especially) require manual approval that can take up to 24 hours. Submit the requests now so they are approved by the time you need them.

### 1.1 Google Earth Engine

GEE is the core of Kairos. It stores the entire Sentinel-1 archive and runs all your analysis server-side on Google's machines. You never download raw satellite data — you just write Python that runs on their servers and returns a map tile URL.

1. Go to **https://signup.earthengine.google.com**
2. Sign in with your Google account.
3. When asked about the type of use, select **"Non-commercial/research"**.
4. For institution, write the name of your project or "Independent researcher" if you have nothing formal.
5. For project description, write something honest like: "Building a web-based SAR analysis platform that uses Sentinel-1 data for flood detection, ship detection, and environmental monitoring. Non-commercial research tool."
6. Submit. You will get a confirmation email. Approval is sometimes instant and sometimes takes a day.

**Important:** Note the Google account you used. Every Google service you set up for Kairos must use this same account, or things get confusing fast.

### 1.2 Google Cloud Platform

GEE runs on top of Google Cloud. You need a GCP project to link them together and to eventually deploy your backend.

1. Go to **https://console.cloud.google.com**
2. Click the project dropdown at the top → **"New Project"**.
3. Name it `kairos`. Note the **Project ID** that GCP generates (it might be `kairos-123456` with numbers appended). You will need this exact ID constantly.
4. Leave the organization blank unless you have one.
5. Click **Create** and wait about 30 seconds.

You do not need to enable any APIs yet — you will do that in Part 4 after software is installed.

### 1.3 Firebase

Firebase handles two things for Kairos: hosting the React frontend and user authentication (Google login). It is linked to your GCP project.

1. Go to **https://console.firebase.google.com**
2. Click **"Add project"**.
3. Select the `kairos` GCP project you just created (it should appear in the dropdown).
4. Firebase will link to it automatically.
5. Disable Google Analytics when asked (you don't need it now).
6. Click **"Continue"** through the remaining screens.

You will come back to Firebase later to enable Authentication. For now, just having the project linked is enough.

### 1.4 Mapbox

Mapbox renders the 3D globe on the frontend. You need a public access token.

1. Go to **https://account.mapbox.com/auth/signup**
2. Create a free account.
3. After signing in, go to your **Account page** (top right).
4. Under "Access tokens", copy the **Default public token**. It starts with `pk.eyJ1`.
5. Save this somewhere — you'll put it in your `.env` file.

The free tier covers 50,000 map loads per month, which is more than enough for development and early launch.

### 1.5 Anthropic API

This is for the Claude integration — the AI layer that parses natural language like "flooding near Dhaka" into structured analysis parameters.

1. Go to **https://console.anthropic.com**
2. Sign up and verify your account.
3. Go to **"API Keys"** in the left sidebar.
4. Click **"Create Key"**, name it `kairos-dev`, and copy the key. It starts with `sk-ant-`.
5. You will need to add a payment method before the API works. Add a card and top up with $20 to start — that covers weeks of development.

Save the key somewhere safe. You cannot view it again after closing the dialog.

### 1.6 GitHub

1. If you do not already have a GitHub account, create one at **https://github.com**.
2. Create a new repository named **`kairos`**.
3. Set it to **Private** (you do not want your API keys accidentally exposed).
4. Do not initialize with a README — you will push an initial commit yourself.

### 1.7 Sentry (optional for Week 1)

Sentry tracks errors. You can skip this for Week 1 and add it in Week 8 when you deploy. If you want it now:
1. Go to **https://sentry.io** and create a free account.
2. Create a Python project and a JavaScript project.
3. Copy both DSN strings — you will need them later.

---

## Part 2 — Install All Software

Open your Terminal and run these commands in order.

### 2.1 Homebrew (macOS only)

Homebrew is a package manager that makes installing everything else much easier.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After it installs, it will tell you to run two commands to add it to your PATH. Run those commands exactly as shown in the terminal output (they are different depending on whether your Mac has Apple Silicon or Intel).

Verify it works:
```bash
brew --version
```

### 2.2 pyenv + Python 3.11

`pyenv` lets you install and switch between Python versions cleanly. Kairos uses Python 3.11 specifically because that is what the context document specifies.

```bash
brew install pyenv
```

Now add pyenv to your shell. If you use zsh (the macOS default):
```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc
```

Install Python 3.11:
```bash
pyenv install 3.11.9
pyenv global 3.11.9
```

Verify:
```bash
python --version
# Should print: Python 3.11.9
```

### 2.3 nvm + Node.js 20

`nvm` manages Node.js versions. You need Node.js 20 for Vite and the frontend build tools.

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc
nvm install 20
nvm use 20
nvm alias default 20
```

Verify:
```bash
node --version
# Should print: v20.x.x
npm --version
```

### 2.4 Docker Desktop

Docker packages your backend into a container for deployment to Cloud Run in Week 8. You need it installed but you will not use it heavily in Week 1.

1. Go to **https://www.docker.com/products/docker-desktop**
2. Download and install the version for your OS.
3. Open Docker Desktop and let it start up. Leave it running in the background.

Verify from terminal:
```bash
docker --version
```

### 2.5 Google Cloud CLI

The `gcloud` command-line tool lets you interact with GCP from your terminal. You need it to authenticate with GEE and eventually deploy to Cloud Run.

```bash
brew install google-cloud-sdk
```

Initialize it and sign in:
```bash
gcloud init
```

This opens a browser window. Sign in with the same Google account you used for GEE and GCP. When asked to select a project, choose `kairos`. When asked about a default compute region, choose `us-central1`.

Also run this to set up Application Default Credentials, which GEE uses:
```bash
gcloud auth application-default login
```

Sign in again when the browser opens.

### 2.6 VS Code

Download from **https://code.visualstudio.com** and install it.

After installing, install these extensions. You can do it from the command line by running each line:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.pylance
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension bradlc.vscode-tailwindcss
code --install-extension github.copilot
```

Open VS Code settings (Cmd+, on Mac) and make these changes:
- Set `"editor.formatOnSave": true`
- Set `"python.defaultInterpreterPath"` to point to your Python 3.11 installation (VS Code will usually detect this automatically)

---

## Part 3 — Create the Project Structure

### 3.1 Clone Your GitHub Repo

```bash
cd ~  # or wherever you keep projects
git clone https://github.com/YOURUSERNAME/kairos.git
cd kairos
```

### 3.2 Create the Folder Structure

Run all of these at once:

```bash
mkdir -p backend/api
mkdir -p backend/models
mkdir -p backend/gee
mkdir -p backend/ai
mkdir -p backend/jobs
mkdir -p frontend/src
```

Your project tree should now look like this:
```
kairos/
  backend/
    api/
    models/
    gee/
    ai/
    jobs/
  frontend/
    src/
```

### 3.3 Create the .gitignore

This stops sensitive files and large generated files from being committed to GitHub.

Create `kairos/.gitignore`:

```
# Environment files — NEVER commit these
.env
.env.local
*.env

# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.egg-info/

# Node
node_modules/
dist/
.next/

# GEE credentials
credentials.json
*-service-account.json

# IDEs
.vscode/settings.json
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
```

### 3.4 Create the .env.example

This is a template that lists every environment variable Kairos needs. You commit this to GitHub (it has no real values) so anyone setting up the project knows what they need.

Create `kairos/.env.example`:

```
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
EE_SERVICE_ACCOUNT=your-gee-service-account-email
EE_PRIVATE_KEY=your-gee-service-account-private-key-json
ANTHROPIC_API_KEY=sk-ant-your-key-here
MAPBOX_PUBLIC_TOKEN=pk.eyJ1your-token-here
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY=your-firebase-service-account-key
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:password@host:5432/kairos
GCS_BUCKET_NAME=kairos-analysis-outputs
SENTRY_DSN_BACKEND=your-sentry-backend-dsn
VITE_MAPBOX_TOKEN=pk.eyJ1your-token-here
VITE_API_BASE_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your-firebase-web-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_SENTRY_DSN=your-sentry-frontend-dsn
```

Now create the actual `kairos/backend/.env` file (this is NOT committed to GitHub):

```
GOOGLE_CLOUD_PROJECT=kairos-YOURPROJECTID
ANTHROPIC_API_KEY=sk-ant-YOURKEYHERE
MAPBOX_PUBLIC_TOKEN=pk.eyJ1YOURTOKENHERE
```

Fill in your real values. The GEE service account fields can be left empty for now — Week 1 uses simpler user-based authentication.

### 3.5 Initial Git Commit

```bash
cd kairos
git add .gitignore .env.example backend/ frontend/
git commit -m "Initial project structure"
git push origin main
```

---

## Part 4 — Google Cloud & GEE Setup

### 4.1 Enable Required APIs in GCP

Go to **https://console.cloud.google.com**, make sure your `kairos` project is selected in the dropdown at the top, then enable these APIs one by one. You can search for each in the search bar:

- **Earth Engine API** — Required for all GEE calls
- **Cloud Run API** — Required for deployment (Week 8)
- **Cloud SQL Admin API** — Required for database (Week 7)
- **Cloud Storage API** — Required for storing outputs
- **Artifact Registry API** — Required for Docker images (Week 8)

For each one: search → click the API → click **"Enable"**.

### 4.2 Authenticate GEE for Local Development

This creates a credentials file on your machine that the GEE Python library reads automatically. You only need to do this once.

First, install the earthengine command-line tool:
```bash
pip install earthengine-api
```

Now authenticate:
```bash
earthengine authenticate
```

This opens a browser window. Sign in with your Google account (the same one you used for GEE signup). It will ask for permissions — grant them all. After signing in, a token is saved to `~/.config/earthengine/credentials`. The GEE Python library reads this file automatically every time you call `ee.Initialize()`.

Now initialize (this links your credentials to your GCP project):
```bash
earthengine initialize --cloud_project kairos-YOURPROJECTID
```

Replace `kairos-YOURPROJECTID` with your actual project ID.

---

## Part 5 — Python Environment and First GEE Test

### 5.1 Create the Virtual Environment

A virtual environment is an isolated Python installation for your project. This means the packages you install for Kairos do not conflict with packages installed globally or for other projects.

```bash
cd kairos/backend
python -m venv venv
```

**Every time you open a new terminal to work on the backend, run this to activate it:**
```bash
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` at the start. That tells you it is active.

To deactivate when you are done:
```bash
deactivate
```

### 5.2 Install Python Packages

With your virtual environment active:

```bash
pip install --upgrade pip
pip install fastapi uvicorn[standard] earthengine-api anthropic pydantic pystac-client python-dotenv httpx redis rq
```

This installs everything needed for Week 1 and the weeks that follow. It will take about 2 minutes.

### 5.3 Run the 3-Line GEE Proof Script

Create a file called `test_gee.py` inside `kairos/backend/`:

```python
import ee
ee.Initialize(project='kairos-YOURPROJECTID')
count = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(ee.Geometry.Rectangle([88.0, 20.0, 92.0, 24.0])).size().getInfo()
print(f"Found {count} Sentinel-1 images over Bangladesh")
```

Replace `kairos-YOURPROJECTID` with your real project ID. Run it:

```bash
python test_gee.py
```

You should see something like:
```
Found 847 Sentinel-1 images over Bangladesh
```

**If you see a number, GEE is working.** This is the first proof that your setup is correct. If you get an error about authentication, go back to Step 4.2 and re-run the authenticate commands.

---

## Part 6 — Set Up Claude Code

Claude Code is the command-line coding assistant you will use to write most of the Kairos code. You tell it what to build, it reads your existing files, and it writes new code directly to your filesystem.

### 6.1 Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:
```bash
claude --version
```

### 6.2 Authenticate Claude Code

```bash
claude
```

The first time you run it, it will ask you to authenticate with your Anthropic account (the same one with your API key). Follow the prompts. Your API key is stored securely on your machine and not committed to any files.

### 6.3 Create the CLAUDE.md File

This is the most important step for making Claude Code useful. When you run `claude` inside your project, it automatically reads `CLAUDE.md` from the project root. This file tells it everything about Kairos: the rules, the patterns, the stack, and what to never do.

Create `kairos/CLAUDE.md` with the following content. Every rule here exists for a reason — the GEE rules especially will save you hours of debugging:

```markdown
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
    
    # ... GEE computation ...
    
    result_image = result_image.clip(geometry)
    map_id_dict = result_image.getMapId({'palette': ['#00BFA8'], 'min': 0, 'max': 1})
    tile_url = map_id_dict['tile_fetcher'].url_format
    
    return {
        'tile_url': tile_url,
        'data_date': data_date,     # actual date string from the satellite imagery used
        # ... analysis-specific stats ...
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
    "function": detect_flood,        # the function to call
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
- All endpoints go in `api/`, one file per endpoint group, each exports a `router = APIRouter()`
- Always wrap GEE function calls in try/except. Catch `ValueError` (user-facing: no data available) separately from `Exception` (server error: GEE failed unexpectedly)
- Use `lifespan` context manager for startup/shutdown logic, not the deprecated `@app.on_event("startup")`

---

## Key GEE Collections

```
COPERNICUS/S1_GRD               Sentinel-1 SAR — the main source for everything
JRC/GSW1_4/GlobalSurfaceWater   Permanent water mask (use to exclude from flood results)
COPERNICUS/DEM/GLO30            30m elevation model (for flood depth estimation)
ESA/WorldCover/v200             Global land cover classification
USDA/NASS/CDL                   US-only crop type map
LANDSAT/LC09/C02/T1_L2          Landsat 9 optical imagery
```

---

## Design Colors — Use These Exactly

- Background: `#0B120E` (near-black with a green tint)
- Accent: `#E8A318` (amber — buttons, CTAs, active states)
- SAR results: `#00BFA8` (teal — all analysis overlays, data badges)
- Surface: `#131A15` (slightly lighter than background — cards, panels)
- Text primary: `#E8EFE9`
- Text secondary: `#8A9E8C`

---

## File Structure

```
backend/
  main.py                 FastAPI app, CORS, GEE init, router includes
  models/
    requests.py           Pydantic models for API requests
    responses.py          Pydantic models for API responses
  api/
    analyze.py            POST /analyze endpoint
    query.py              POST /query endpoint (AI natural language)
    scenes.py             GET /scenes endpoint
    registry.py           GET /registry endpoint
  gee/
    registry.py           AnalysisRegistry dict
    flood.py              Flood extent detection
    ships.py              Ship detection
    fire.py               Wildfire burn scar
    oil.py                Oil spill detection
    deforestation.py      Deforestation mapping
    ice.py                Sea ice extent
  ai/
    client.py             Anthropic API client
    system_prompt.md      The Kairos Claude system prompt
    parser.py             Response parser and validator
  jobs/
    queue.py              Redis queue setup
    worker.py             Background job worker
  requirements.txt
  Dockerfile

frontend/
  src/
    App.tsx
    main.tsx
    stores/
      mapStore.ts         Globe state: center, zoom, layers, AOI
      sidebarStore.ts     Sidebar state: step, selected task, job, result
      chatStore.ts        Chat state: messages, loading
      authStore.ts        Auth state: user, token
    components/
      Globe.tsx
      Sidebar/
        Sidebar.tsx
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

Week 1 in progress. GEE authenticated. Building flood detection function and FastAPI skeleton.

---

## Example Prompts That Work Well With This Codebase

Good prompts (specific, reference existing patterns):
- "Write a ship detection GEE function in `gee/ships.py` following the exact same pattern as `gee/flood.py`. It should use CFAR detection on the VV band and return tile_url, vessel_count, and data_date."
- "Add `ship_detection` to the AnalysisRegistry in `gee/registry.py` using the same structure as the flood_extent entry."
- "The `/analyze` endpoint in `api/analyze.py` is returning a 422 error for this request body: [paste body]. Fix the Pydantic model in `models/requests.py` to accept it."
- "Write a Pydantic response model in `models/responses.py` for the analyze endpoint that includes tile_url, flood_area_km2, confidence, and data_date."

Bad prompts (too vague, Claude can't help well):
- "Add ship detection" — doesn't say where or which pattern to follow
- "Fix the backend" — too vague
- "Make it better" — no specific target
```

That file (`CLAUDE.md`) goes in the root of your `kairos/` directory, alongside `.gitignore`. Commit it to GitHub — it is not sensitive.

### 6.4 How to Use Claude Code Day-to-Day

Run `claude` from inside your `kairos/` directory. It reads all your files and the CLAUDE.md automatically.

**The most effective workflow is:**
1. Tell Claude Code exactly what file to create and reference an existing pattern: "Write `gee/ships.py` following the exact pattern in `gee/flood.py`."
2. One task per message. Do not ask it to write five files at once — quality drops.
3. After it writes code, run it immediately. If there is an error, paste the exact error message back to Claude Code: "Got this error when running: [paste error]."
4. For functions with GEE, always test the function directly in Python before testing it through FastAPI. `python -c "from gee.flood import detect_flood; print(detect_flood([88, 20, 92, 24], '2024-08-01', '2024-08-31'))"` is faster than restarting the server every time.

**Use this chat interface (Claude.ai) for decisions, use Claude Code for writing code.** When you are not sure which design to pick, ask here. When you know what to build, switch to Claude Code.

---

## Part 7 — Build the FastAPI Backend

Now you build the actual code. Your venv should be active (`source venv/bin/activate`).

### 7.1 Create requirements.txt

Create `kairos/backend/requirements.txt`:

```
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
earthengine-api>=0.1.380
anthropic>=0.30.0
pydantic>=2.0.0
pystac-client>=0.7.0
python-dotenv>=1.0.0
httpx>=0.25.0
redis>=5.0.0
rq>=1.16.0
```

### 7.2 Write the Flood Detection GEE Function

Create `kairos/backend/gee/__init__.py` (empty file — tells Python this is a package):
```bash
touch backend/gee/__init__.py
touch backend/api/__init__.py
touch backend/models/__init__.py
touch backend/ai/__init__.py
touch backend/jobs/__init__.py
```

Create `kairos/backend/gee/flood.py`:

```python
import ee
from datetime import datetime, timedelta


def detect_flood(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Detect flood extent using Sentinel-1 SAR backscatter change detection.

    Flooded areas appear dark in SAR because water reflects radar away from
    the satellite. By comparing post-flood backscatter to a pre-flood baseline,
    we find pixels that got significantly darker, indicating new inundation.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date: 'YYYY-MM-DD' — start of the flood period to analyze
        end_date: 'YYYY-MM-DD' — end of the flood period to analyze

    Returns:
        dict with tile_url, flood_area_km2, confidence, data_date, post_images_used

    Raises:
        ValueError: if no Sentinel-1 data exists for this location and date range
    """
    geometry = ee.Geometry.Rectangle(bbox)

    # Parse dates to compute the pre-event baseline window
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')

    # Pre-event baseline: 30 days immediately before the flood period
    pre_end = start_dt - timedelta(days=1)
    pre_start = pre_end - timedelta(days=30)

    # Base Sentinel-1 collection filtered to IW mode (interferometric wide swath)
    # and VV polarization (vertical transmit, vertical receive — best for water)
    s1 = (
        ee.ImageCollection('COPERNICUS/S1_GRD')
        .filter(ee.Filter.eq('instrumentMode', 'IW'))
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
        .select('VV')
        .filterBounds(geometry)
    )

    # Post-event: images during the flood period
    post_collection = s1.filterDate(start_date, end_date)
    post_count = post_collection.size().getInfo()

    if post_count == 0:
        raise ValueError(
            f"No Sentinel-1 data found for bbox {bbox} between {start_date} and {end_date}. "
            "Try a wider date range or check that the location is within Sentinel-1 coverage."
        )

    # Pre-event: baseline images for comparison
    pre_collection = s1.filterDate(
        pre_start.strftime('%Y-%m-%d'),
        pre_end.strftime('%Y-%m-%d')
    )
    pre_count = pre_collection.size().getInfo()

    # If 30-day window has no data, extend to 60 days
    if pre_count == 0:
        pre_start = start_dt - timedelta(days=60)
        pre_collection = s1.filterDate(
            pre_start.strftime('%Y-%m-%d'),
            pre_end.strftime('%Y-%m-%d')
        )
        pre_count = pre_collection.size().getInfo()

    if pre_count == 0:
        raise ValueError(
            "No pre-event Sentinel-1 data found for baseline comparison. "
            "This area may have limited coverage. Try a different location."
        )

    # Mean composites reduce speckle noise (SAR images are inherently noisy)
    post_mean = post_collection.mean()
    pre_mean = pre_collection.mean()

    # dB difference: post minus pre
    # Flooded pixels show a DROP in backscatter (water = dark = low dB)
    diff = post_mean.subtract(pre_mean)

    # Threshold: pixels where backscatter dropped by more than 3 dB are likely flooded
    flood_mask = diff.lt(-3)

    # Remove permanent water bodies so we only show NEW flooding
    # JRC 'occurrence' = % of time a pixel was water historically (0-100)
    jrc = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
    permanent_water = jrc.gt(75)  # more than 75% historically wet = permanent water

    # Subtract permanent water from flood mask, then apply the mask
    new_flood = flood_mask.where(permanent_water, 0)
    new_flood = new_flood.selfMask()  # removes non-flooded pixels from the layer entirely

    # Clip to the user's AOI
    new_flood = new_flood.clip(geometry)

    # Generate a Mapbox-compatible tile URL
    # The teal color (#00BFA8) is Kairos's color for SAR analysis results
    map_id_dict = new_flood.getMapId({
        'palette': ['#00BFA8'],
        'min': 0,
        'max': 1,
    })
    tile_url = map_id_dict['tile_fetcher'].url_format

    # Calculate total flood area in km²
    # pixelArea() returns each pixel's area in m², multiply by flood mask (0 or 1)
    pixel_area = new_flood.multiply(ee.Image.pixelArea())
    area_result = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=30,         # 30m scale is appropriate for Sentinel-1 (10m native, 30m avoids timeout)
        maxPixels=1e10,
        bestEffort=True   # automatically reduces scale if needed to avoid GEE memory limits
    ).getInfo()

    flood_area_m2 = area_result.get('VV', 0) or 0
    flood_area_km2 = round(float(flood_area_m2) / 1_000_000, 2)

    # Get the date of the most recent post-event image used
    latest_image = post_collection.sort('system:time_start', False).first()
    data_date = (
        ee.Date(latest_image.get('system:time_start'))
        .format('YYYY-MM-dd')
        .getInfo()
    )

    return {
        'tile_url': tile_url,
        'flood_area_km2': flood_area_km2,
        'confidence': 0.85,          # static placeholder — proper confidence scoring comes later
        'data_date': data_date,
        'post_images_used': post_count,
        'pre_images_used': pre_count,
    }
```

### 7.3 Write the Analysis Registry

Create `kairos/backend/gee/registry.py`:

```python
from gee.flood import detect_flood

# This dictionary is the single source of truth for all Kairos analysis types.
# To add a new analysis type:
#   1. Write the GEE function in a new file (e.g. gee/ships.py)
#   2. Import it here
#   3. Add one entry to this dict
#   4. Nothing else in the codebase needs to change

ANALYSIS_REGISTRY = {
    "flood_extent": {
        "function": detect_flood,
        "display_name": "Flood Extent Mapping",
        "description": (
            "Detects surface water inundation by measuring the drop in Sentinel-1 VV "
            "backscatter compared to a pre-flood baseline. Water returns almost no radar "
            "signal so flooded areas appear as anomalously dark patches."
        ),
        "category": "Disaster Response",
        "data_sources": ["S1"],          # shown as badges in the frontend sidebar
        "estimated_seconds": 15,
        "output_type": "raster",
        "color_palette": ["#00BFA8"],
        "icon": "waves"
    }
}
```

### 7.4 Write the Pydantic Models

Create `kairos/backend/models/__init__.py` (empty).

Create `kairos/backend/models/requests.py`:

```python
from pydantic import BaseModel, field_validator
from typing import List


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze"""
    analysis_type: str                     # must match a key in ANALYSIS_REGISTRY
    bbox: List[float]                      # [min_lon, min_lat, max_lon, max_lat]
    start_date: str                        # YYYY-MM-DD
    end_date: str                          # YYYY-MM-DD

    @field_validator('bbox')
    @classmethod
    def validate_bbox(cls, v):
        if len(v) != 4:
            raise ValueError('bbox must have exactly 4 values: [min_lon, min_lat, max_lon, max_lat]')
        min_lon, min_lat, max_lon, max_lat = v
        if min_lon >= max_lon:
            raise ValueError('min_lon must be less than max_lon')
        if min_lat >= max_lat:
            raise ValueError('min_lat must be less than max_lat')
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError('Longitude values must be between -180 and 180')
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError('Latitude values must be between -90 and 90')
        return v
```

### 7.5 Write the /analyze Endpoint

Create `kairos/backend/api/analyze.py`:

```python
from fastapi import APIRouter, HTTPException
from models.requests import AnalyzeRequest
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()


@router.post("/analyze")
def analyze(request: AnalyzeRequest):
    """
    Run a SAR analysis for a given area and date range.

    Returns a Mapbox tile URL plus statistics.
    The tile URL can be used directly as a raster source in Mapbox GL JS.
    """

    # Check that the requested analysis type exists in the registry
    if request.analysis_type not in ANALYSIS_REGISTRY:
        available = list(ANALYSIS_REGISTRY.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown analysis type '{request.analysis_type}'. Available types: {available}"
        )

    config = ANALYSIS_REGISTRY[request.analysis_type]
    analysis_fn = config["function"]

    try:
        result = analysis_fn(
            bbox=request.bbox,
            start_date=request.start_date,
            end_date=request.end_date
        )
    except ValueError as e:
        # User-facing errors: no data available, bad location, etc.
        # Return 400 so the frontend knows this is something the user can fix
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected GEE errors, timeouts, etc.
        # Return 500 — this is a server problem, not a user problem
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Return the full result with request context attached
    return {
        "analysis_type": request.analysis_type,
        "display_name": config["display_name"],
        "bbox": request.bbox,
        "start_date": request.start_date,
        "end_date": request.end_date,
        **result
    }
```

### 7.6 Write the /registry Endpoint

Create `kairos/backend/api/registry.py`:

```python
from fastapi import APIRouter
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()


@router.get("/registry")
def get_registry():
    """
    Return all available analysis types and their metadata.

    The frontend uses this to build the sidebar task list.
    Adding a new analysis type to ANALYSIS_REGISTRY automatically
    makes it appear here — no other changes needed.
    """
    return [
        {
            "id": analysis_id,
            "display_name": config["display_name"],
            "description": config["description"],
            "category": config["category"],
            "data_sources": config["data_sources"],
            "estimated_seconds": config["estimated_seconds"],
            "output_type": config["output_type"],
            "icon": config.get("icon", "satellite")
        }
        for analysis_id, config in ANALYSIS_REGISTRY.items()
    ]
```

### 7.7 Write main.py

Create `kairos/backend/main.py`:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import ee

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize GEE on startup."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable is not set")
    try:
        ee.Initialize(project=project_id)
        print(f"✓ Google Earth Engine initialized for project: {project_id}")
    except Exception as e:
        print(f"✗ GEE initialization failed: {e}")
        raise
    yield
    # Nothing to clean up on shutdown


app = FastAPI(
    title="Kairos API",
    description="SAR satellite analysis platform",
    version="0.1.0",
    lifespan=lifespan
)

# CORS: allow the React frontend (Vite dev server on port 5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # in case you use a different port
        "https://kairos.earth",    # production frontend — update when you have a domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include endpoint routers
from api.analyze import router as analyze_router
from api.registry import router as registry_router

app.include_router(analyze_router)
app.include_router(registry_router)


@app.get("/health")
def health():
    """Health check endpoint. Used by Cloud Run to verify the service is alive."""
    return {"status": "ok", "version": "0.1.0"}
```

### 7.8 Run the Server and Test

Make sure your virtual environment is active, then from inside `kairos/backend/`:

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Started server process [12345]
✓ Google Earth Engine initialized for project: kairos-YOURID
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

The `--reload` flag means the server automatically restarts when you change a file. Leave this running in one terminal tab.

**Test the health endpoint:**
```bash
curl http://localhost:8000/health
```
Expected response: `{"status":"ok","version":"0.1.0"}`

**Test the registry endpoint:**
```bash
curl http://localhost:8000/registry
```
Expected response: a JSON array with one entry for `flood_extent`.

---

## Part 8 — The Week 1 Proof Tests

### Proof 1: GEE Script Works

You should have already run this in Part 5. Run it again to confirm:

```bash
python test_gee.py
```

Expected: `Found [some large number] Sentinel-1 images over Bangladesh`

### Proof 2: curl Returns a Real Tile URL

This is the main Week 1 proof. Run this curl command (your server must be running):

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "flood_extent",
    "bbox": [88.0, 20.0, 92.0, 24.0],
    "start_date": "2024-08-01",
    "end_date": "2024-08-31"
  }' \
  | python -m json.tool
```

This uses Bangladesh in August 2024, which had real major flooding events. GEE has the data.

Expected response (takes 10–20 seconds while GEE processes):
```json
{
  "analysis_type": "flood_extent",
  "display_name": "Flood Extent Mapping",
  "bbox": [88.0, 20.0, 92.0, 24.0],
  "start_date": "2024-08-01",
  "end_date": "2024-08-31",
  "tile_url": "https://earthengine.googleapis.com/v1/projects/earthengine-public/maps/SOME_MAP_ID/tiles/{z}/{x}/{y}",
  "flood_area_km2": 342.18,
  "confidence": 0.85,
  "data_date": "2024-08-27",
  "post_images_used": 12,
  "pre_images_used": 8
}
```

**Week 1 is complete when you see a response like this with a real tile URL.**

### Bonus: Visually Confirm the Tile URL Works

Create a file `kairos/backend/test_map.html` with this content. Open it in your browser after pasting your tile URL and Mapbox token into it:

```html
<!DOCTYPE html>
<html>
<head>
  <script src='https://api.mapbox.com/mapbox-gl-js/v3.5.0/mapbox-gl.js'></script>
  <link href='https://api.mapbox.com/mapbox-gl-js/v3.5.0/mapbox-gl.css' rel='stylesheet' />
  <style>body { margin: 0; } #map { width: 100vw; height: 100vh; }</style>
</head>
<body>
  <div id='map'></div>
  <script>
    mapboxgl.accessToken = 'PASTE_YOUR_MAPBOX_TOKEN_HERE';
    const map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [90.4, 22.3],
      zoom: 7
    });
    map.on('load', () => {
      map.addSource('flood', {
        type: 'raster',
        tiles: ['PASTE_YOUR_TILE_URL_HERE'],
        tileSize: 256
      });
      map.addLayer({
        id: 'flood-layer',
        type: 'raster',
        source: 'flood',
        paint: { 'raster-opacity': 0.8 }
      });
    });
  </script>
</body>
</html>
```

Open it in your browser. You should see a dark Mapbox map of Bangladesh with teal flood extent areas. This is real Sentinel-1 radar data processed by Google Earth Engine.

---

## Common Errors and Fixes

**"No project found" from GEE Initialize**  
You forgot to pass the project ID. Make sure `GOOGLE_CLOUD_PROJECT` is set in your `.env` file and that `load_dotenv()` is called before `ee.Initialize()`.

**"403 Forbidden" or "EEException" from GEE**  
Your GEE account is not yet approved, or you authenticated with a different Google account. Check that approval email and re-run `earthengine authenticate`.

**"ModuleNotFoundError: No module named 'gee'"**  
Your virtual environment is not active, or you are running `uvicorn` from the wrong directory. Run `source venv/bin/activate` then `cd kairos/backend` then `uvicorn main:app --reload`.

**"422 Unprocessable Entity" from FastAPI**  
The request body doesn't match the Pydantic model. Check that your JSON has `analysis_type`, `bbox` (4 floats), `start_date`, and `end_date` (YYYY-MM-DD strings).

**Tile URL returns a blank gray layer in Mapbox**  
The flood detection ran but found no flooding, so the result image has no visible pixels. Try a different date range with a known flooding event, or try the 2017 Bangladesh monsoon floods: `"start_date": "2017-08-01", "end_date": "2017-08-31"`.

---

## What You Now Have at the End of Week 1

- All accounts created and authenticated
- Full development environment configured
- GEE returning real satellite data from Python
- FastAPI server running with a working `/analyze` endpoint and `/registry` endpoint
- Flood detection producing real tile URLs backed by actual Sentinel-1 data
- Claude Code set up with a CLAUDE.md that understands the whole project
- Clean project structure ready to build Week 2 on top of

The Week 2 goal is to add ship detection and the Claude AI `/query` endpoint so natural language like "flooding near Dhaka" routes to the right analysis automatically.
```
