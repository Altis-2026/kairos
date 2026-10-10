# Deployment

Kairos runs as two pieces: a static React frontend and a FastAPI backend.

## Backend on Google Cloud Run

`.github/workflows/deploy.yml` builds `backend/Dockerfile`, pushes it to Artifact
Registry and deploys the `kairos-api` service to Cloud Run in `us-central1` on
every push to `main`. The service runs with 1 GiB of memory, a 300 second request
timeout and one warm instance, under a dedicated service account that is
registered with Earth Engine.

Repository secrets used by the workflow:

| Secret | Purpose |
|---|---|
| `GCP_PROJECT_ID` | The Google Cloud project registered with Earth Engine |
| `GCP_SA_KEY` | Service account key with Cloud Run Admin, Artifact Registry Writer and Service Account User |
| `OPENROUTER_API_KEY` | Language model access for the chat, explanations and Janus |
| `VITE_MAPBOX_TOKEN`, `VITE_API_BASE_URL` | Used by the frontend build check |

`.github/workflows/keep-warm.yml` pings `/health` every ten minutes so the
service never cold-starts.

Optional runtime variables are documented in `backend/.env.example`, including
the free-tier limits, the result cache lifetime, the sweep token and the featured
story refresh interval.

## Frontend on Vercel

The production frontend deploys through Vercel's GitHub integration. Set
`VITE_MAPBOX_TOKEN` and `VITE_API_BASE_URL` in the Vercel project, and optionally
the three `VITE_FIREBASE_*` values to enable sign-in. The build command is
`npm run build` and the output directory is `frontend/dist`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request: Ruff and pytest
for the backend, then typecheck, ESLint, Vitest and a production build for the
frontend.

## Keeping it free

- Earth Engine is free for noncommercial and research use.
- Mapbox includes 50,000 map loads a month on the free tier.
- Per-IP limits and a daily AI ceiling cap language model spend.
- The result cache and the featured story warmer mean repeat visits cost nothing.
