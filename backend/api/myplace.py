import httpx
from fastapi import APIRouter, HTTPException

from models.requests import MyPlaceRequest

router = APIRouter()

CENSUS_URL = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

HALF_LON = 0.06
HALF_LAT = 0.045


def _census_geocode(client: httpx.Client, address: str):
    resp = client.get(
        CENSUS_URL,
        params={
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        },
    )
    resp.raise_for_status()
    matches = resp.json().get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    m = matches[0]
    coords = m.get("coordinates", {})
    lon, lat = coords.get("x"), coords.get("y")
    if lon is None or lat is None:
        return None
    return {
        "label": m.get("matchedAddress") or address,
        "lon": float(lon),
        "lat": float(lat),
        "source": "US Census Bureau geocoder",
    }


def _nominatim_geocode(client: httpx.Client, address: str):
    resp = client.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "kairos-sar-education/1.0"},
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    r = results[0]
    return {
        "label": r.get("display_name") or address,
        "lon": float(r["lon"]),
        "lat": float(r["lat"]),
        "source": "OpenStreetMap Nominatim",
    }


@router.post("/myplace/locate")
def locate_place(request: MyPlaceRequest):
    hit = None
    errors = []
    with httpx.Client(timeout=20.0) as client:
        try:
            hit = _census_geocode(client, request.address)
        except Exception as e:
            errors.append(f"census: {e}")
        if hit is None:
            try:
                hit = _nominatim_geocode(client, request.address)
            except Exception as e:
                errors.append(f"nominatim: {e}")

    if hit is None:
        if errors:
            raise HTTPException(
                status_code=502,
                detail="Both geocoding services failed; try again in a moment.",
            )
        return {"found": False}

    lon, lat = hit["lon"], hit["lat"]
    bbox = [
        round(lon - HALF_LON, 5),
        round(lat - HALF_LAT, 5),
        round(lon + HALF_LON, 5),
        round(lat + HALF_LAT, 5),
    ]
    return {
        "found": True,
        "label": hit["label"],
        "lon": lon,
        "lat": lat,
        "bbox": bbox,
        "source": hit["source"],
    }
