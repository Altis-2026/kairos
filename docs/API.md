# Kairos API

Programmatic access to every analysis Kairos runs. Base URL is your deployed
backend (e.g. `https://kairos-api-....run.app`). Interactive docs live at
`/docs` (OpenAPI/Swagger) on the running server.

## Authentication

Public data endpoints are open during early access. To identify your calls
(and be ready for team quotas), mint an API key and send it as a header:

```
X-API-Key: krs_...
```

- `POST /keys` `{"owner": "you", "label": "lab-pipeline"}` → the full key,
  shown once. Only a SHA-256 hash is stored.
- `GET /keys?owner=you` → your key prefixes.
- `DELETE /keys/{prefix}?owner=you` → revoke.
- `GET /keys/usage?owner=you&days=30` → your call counts per endpoint.

## Core analysis

```
POST /analyze
{
  "analysis_type": "flood_extent",
  "bbox": [90.2, 23.6, 90.6, 24.0],
  "start_date": "2024-08-15",
  "end_date": "2024-09-05"
}
```

Returns `tile_url` (XYZ raster tiles), `headline_stat`, `confidence`,
`stats` (uncertainty ranges, optical agreement, method notes) and a
`provenance` block (SHA-256 + HMAC signature). 21 analysis types —
enumerate them with `GET /registry`.

`POST /verify` with a previously returned result checks its provenance
signature: any change to the scientific content invalidates it.

## Research workbench

- `POST /research/signal` — per-scene time series of `VV`/`VH`/`NDVI`/
  `NDWI`/`NDSI` over a bbox (optical from Sentinel-2 or `"source": "HLS"`
  for Landsat). Returns points, OLS + Mann-Kendall trend statistics with
  real p-values, a CSV, and a publication SVG chart.
- `POST /research/compare_analyses` — the same analysis over two sites or
  two windows: `{"analysis_type", "a": {bbox, start_date, end_date, label},
  "b": {...}}` → both results, delta, delta %, and a comparison figure.
- `POST /research/cog_preview` — render your own Cloud-Optimized GeoTIFF
  (`{"uri": "gs://bucket/scene.tif"}`) as map tiles. Beta; GCS-hosted COGs.
- `POST /research/backscatter`, `/research/optical`, `/research/compare`,
  `/research/timeseries` — raw SAR, true-color, before/after, and animated
  analysis frames.

## Validation and trust

- `GET /validation/benchmarks`, `POST /validation/run` — score the
  production detectors against independently mapped events.
- `GET /scoreboard` — the public accuracy scoreboard: every validation run
  ever executed, aggregated. No auth; being public is the point.

## Watching and alerting

- `POST /alerts/check` — has a new pass produced something over this AOI?
- `POST /alerts/webhook` `{"owner", "url"}` — register an outbound webhook;
  watch findings POST there (Slack incoming-webhook URLs are formatted
  automatically). `POST /alerts/webhook/test` sends a sample event.
- `POST /portfolios` — register up to 50 named sites, then
  `POST /portfolios/{id}/digest` sweeps them all and flags which have fresh
  imagery worth analyzing right now.

## Janus (research mentor) surface

Project-scoped endpoints under `/janus/...` (see `/docs`): projects, chat,
datasets (upload GeoJSON/CSV ground truth; validate any analysis against it),
figures (`results`, `study_area`, `validation` as SVG), exports (LaTeX with
`?journal=ieee`, BibTeX, RIS, Google-Docs HTML, policy brief), peer review,
sharing (`POST /janus/projects/{id}/members`), and the reproducibility pack.

## Notes

- Analyses are synchronous and can take 10-60 s — set client timeouts
  accordingly.
- `bbox` is `[min_lon, min_lat, max_lon, max_lat]`, dates are `YYYY-MM-DD`.
- Every error body is `{"detail": "..."}` with an honest, actionable message.
