# Kairos API

The backend is a FastAPI service. Interactive documentation is served at `/docs`
on any running instance. All request and response bodies are JSON.

## Limits

The API is free and open. To keep it that way for everyone, each visitor IP gets
60 AI requests and 120 compute requests per hour, and the whole service has a
daily ceiling on AI calls. A request over the limit returns `429` with a message
that explains what still works. Operators can change the limits with the
`RATE_AI_PER_HOUR`, `RATE_COMPUTE_PER_HOUR` and `DAILY_AI_CEILING` variables.

Identical analysis requests within six hours are served from a cache.

## Analyses

```
POST /analyze
{
  "analysis_type": "flood_extent",
  "bbox": [90.2, 23.6, 90.6, 24.0],
  "start_date": "2024-08-15",
  "end_date": "2024-09-05",
  "polygon": [[90.2, 23.6], [90.6, 23.7], [90.4, 24.0]]
}
```

`polygon` is optional. When it is present the analysis runs inside that shape
instead of the box. The response contains `tile_url` (XYZ raster tiles),
`headline_stat`, `confidence`, `data_date`, `stats` (uncertainty ranges, optical
agreement, method notes), `mode` (`observed` or `simulated`) and a `provenance`
block with a SHA-256 hash and HMAC signature.

| Endpoint | Purpose |
|---|---|
| `GET /registry` | Every analysis type with its description, sensors and timing |
| `GET /scenes` | Sentinel-1 passes available for an area and window |
| `POST /verify` | Check that a returned result has not been altered |
| `GET /featured`, `POST /featured/{id}` | The featured stories and their results |
| `POST /simulate`, `GET /simulate/scenes` | Run a flood or wildfire simulation, list showcase scenes |
| `GET /status/{job_id}` | Poll a queued simulation |

## Language

```
POST /query
{
  "query": "was there flooding near Kerrville in July 2025?",
  "viewport_bbox": [-100, 29, -98, 31],
  "history": [{"role": "user", "content": "..."}, {"role": "kairos", "content": "..."}],
  "language": "en"
}
```

Returns `understood`, `clarification` (when the question needs one), `parameters`
(what the model extracted, including its reasoning), `result`, `results` (when one
question asked for several analyses) and `explanation`.

| Endpoint | Purpose |
|---|---|
| `POST /interpret` | Plain-language interpretation of a result |
| `POST /interpret/context` | Recent regional news and reports, with sources |
| `POST /agent/plan`, `POST /agent/report` | Turn a goal into up to four analyses, then write a report |

## Places and preparedness

| Endpoint | Purpose |
|---|---|
| `POST /myplace/locate` | Geocode an address for My Place |
| `POST /foresight`, `POST /foresight/ask` | Hazard exposure outlook and questions about it |
| `GET /districts/lookup?state=TX&number=26` | A congressional district boundary for the current Congress |
| `GET /districts/locate?lon=..&lat=..` | The district containing a point |
| `POST /export/briefing` | A printable situation briefing built from findings |
| `POST /impact/population` | People and buildings inside a detection footprint |

## Research

| Endpoint | Purpose |
|---|---|
| `POST /research/backscatter`, `/optical`, `/compare`, `/timeseries`, `/signal` | Raw radar, optical, before and after, time series, trend statistics |
| `POST /research/compare_analyses` | The same analysis over two places or windows |
| `GET /validation/benchmarks`, `POST /validation/run` | Measured accuracy against reference datasets |
| `POST /confounders` | Rainfall, wind and land-cover checks for innocent explanations |
| `GET /scoreboard` | Public accuracy summary |
| `POST /vessels/screen`, `GET /vessels/cases` | Dark-vessel screening against AIS |
| `GET /insar/sites`, `GET /insar/data/{site}/{kind}` | Published interferograms |
| `POST /export/geotiff`, `POST /export/report` | GeoTIFF download link and methodology report |

## Monitoring

| Endpoint | Purpose |
|---|---|
| `GET /feed`, `GET /feed/status` | Findings from the autonomous sweeper |
| `POST /feed/sweep` | Start a sweep. Needs the `X-Sweep-Token` header |
| `POST /alerts/check`, `/alerts/webhook` | New-pass checks and webhook delivery |
| `POST /portfolios`, `GET /portfolios` | Monitor many sites at once |
| `POST /keys`, `GET /keys/usage` | Optional API keys to identify your calls |

## Janus

`/janus/*` endpoints manage research projects, chat turns, datasets, citations and
exports. See [JANUS.md](JANUS.md).

## Health

`GET /health` reports the service, whether Earth Engine is ready and whether the
language model is configured.
