import httpx
from fastapi import APIRouter

from models.requests import EventsRequest

router = APIRouter()

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

_CATEGORY_COLOR = {
    "wildfires": "#E8541E",
    "floods": "#3BA7FF",
    "severeStorms": "#7B61FF",
    "volcanoes": "#E84855",
    "seaLakeIce": "#BFEFFF",
    "earthquakes": "#C77DFF",
    "landslides": "#E8A318",
    "drought": "#D9A441",
}


def _representative_point(geometry: list):
    if not geometry:
        return None, None
    latest = geometry[-1]
    coords = latest.get("coordinates")
    gtype = (latest.get("type") or "").lower()
    if coords is None:
        return None, None
    try:
        if gtype == "point":
            return float(coords[0]), float(coords[1])
        ring = coords[0]
        lons = [float(p[0]) for p in ring]
        lats = [float(p[1]) for p in ring]
        return sum(lons) / len(lons), sum(lats) / len(lats)
    except (TypeError, ValueError, IndexError):
        return None, None


def _transform(events: list) -> list:
    out = []
    for ev in events:
        lon, lat = _representative_point(ev.get("geometry", []))
        if lon is None:
            continue
        cats = ev.get("categories") or [{}]
        cat_id = cats[0].get("id", "")
        cat_title = cats[0].get("title", "Event")
        geom = ev.get("geometry") or [{}]
        date = geom[-1].get("date", "")
        sources = ev.get("sources") or []
        link = ev.get("link") or (sources[0].get("url") if sources else None)
        out.append(
            {
                "id": ev.get("id"),
                "title": ev.get("title", "Untitled event"),
                "category": cat_title,
                "category_id": cat_id,
                "color": _CATEGORY_COLOR.get(cat_id, "#8A9E8C"),
                "date": date[:10] if date else "",
                "lon": lon,
                "lat": lat,
                "closed": bool(ev.get("closed")),
                "link": link,
            }
        )
    return out


@router.post("/events/historical")
def historical_events(req: EventsRequest):
    min_lon, min_lat, max_lon, max_lat = req.bbox
    eonet_bbox = f"{min_lon},{max_lat},{max_lon},{min_lat}"
    params = {
        "bbox": eonet_bbox,
        "status": req.status,
        "days": req.days,
        "limit": 200,
    }
    if req.category:
        params["category"] = req.category

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(EONET_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        return {
            "available": False,
            "events": [],
            "source": "NASA EONET",
            "note": (
                "Historical events feed is unreachable from this deployment "
                f"({type(e).__name__}). It populates automatically wherever "
                "outbound access to eonet.gsfc.nasa.gov is allowed."
            ),
        }

    events = _transform(payload.get("events", []))
    events.sort(key=lambda e: e["date"], reverse=True)
    return {
        "available": True,
        "events": events,
        "count": len(events),
        "source": "NASA EONET",
    }
