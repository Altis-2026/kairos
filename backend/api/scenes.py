import ee
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/scenes")
def get_scenes(
    min_lon: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="Invalid bbox ordering.")

    try:
        geometry = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
        collection = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .sort("system:time_start")
        )

        info = collection.limit(200).getInfo()
        features = info.get("features", [])

        scenes = []
        for f in features:
            props = f.get("properties", {})
            ts = props.get("system:time_start")
            date = ""
            if ts:
                import datetime as _dt

                date = _dt.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            scenes.append(
                {
                    "scene_id": f.get("id", ""),
                    "date": date,
                    "orbit_direction": props.get("orbitProperties_pass", "UNKNOWN"),
                    "instrument_mode": props.get("instrumentMode", "UNKNOWN"),
                    "polarizations": props.get("transmitterReceiverPolarisation", []),
                }
            )

        return {
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "start_date": start_date,
            "end_date": end_date,
            "scene_count": len(scenes),
            "scenes": scenes,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scene lookup failed: {e}")
