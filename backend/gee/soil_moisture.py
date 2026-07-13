from datetime import datetime, timedelta

import ee

from gee import common


def estimate_soil_moisture(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    recent = s1.filterDate(start_date, end_date)
    recent_count = common.require_images(
        recent, f"this area between {start_date} and {end_date}"
    )

    hist_end = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=1)
    hist_start = hist_end - timedelta(days=365)
    hist = s1.filterDate(
        hist_start.strftime("%Y-%m-%d"), hist_end.strftime("%Y-%m-%d")
    )
    hist_count = common.require_images(hist, "the 12-month reference period")

    dry_ref = hist.min()
    wet_ref = hist.max()
    span = wet_ref.subtract(dry_ref)

    index = (
        recent.mean()
        .subtract(dry_ref)
        .divide(span)
        .clamp(0, 1)
        .updateMask(span.gte(3))
        .rename("moisture")
    )

    water = common.permanent_water_mask(50)
    index = index.updateMask(water.Not()).clip(geometry)

    stats = index.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=60,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_index = round(float(stats.get("moisture") or 0), 2)

    dry = index.lt(0.25).selfMask()
    dry_km2 = common.area_km2(dry, geometry, band="moisture", scale=60)
    valid_km2 = common.area_km2(
        index.gte(0).selfMask(), geometry, band="moisture", scale=60
    )
    dry_fraction = round(dry_km2 / valid_km2, 2) if valid_km2 else 0

    url = common.tile_url(
        index,
        {
            "palette": ["#8B5A2B", "#D9A441", "#7BC043", "#00BFA8", "#1E6FE8"],
            "min": 0,
            "max": 1,
        },
    )

    return {
        "tile_url": url,
        "result_image": index,
        "mean_moisture_index": mean_index,
        "dry_soil_fraction": dry_fraction,
        "dry_soil_km2": dry_km2,
        "confidence": round(min(0.82, 0.55 + 0.02 * recent_count), 2),
        "data_date": common.latest_image_date(recent),
        "recent_images_used": recent_count,
        "reference_images_used": hist_count,
        "headline_stat": {
            "label": "Mean soil moisture index",
            "value": mean_index,
            "unit": "(0 dry to 1 wet)",
        },
    }
