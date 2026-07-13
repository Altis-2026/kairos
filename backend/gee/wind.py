import ee

from gee import common


def estimate_ocean_wind(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    period = s1.filterDate(start_date, end_date)
    image_count = common.require_images(
        period, f"this area between {start_date} and {end_date}"
    )

    water = common.permanent_water_mask(50)
    composite = period.mean().updateMask(water)

    wind = (
        composite.add(25)
        .divide(20)
        .multiply(18)
        .clamp(0, 28)
        .rename("wind")
        .clip(geometry)
    )

    stats = wind.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=geometry,
        scale=100,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_wind = round(float(stats.get("wind_mean") or 0), 1)
    max_wind = round(float(stats.get("wind_max") or 0), 1)

    calm = wind.lt(3).selfMask()
    calm_km2 = common.area_km2(calm, geometry, band="wind", scale=100)
    water_km2 = common.area_km2(
        water.rename("wind").selfMask().clip(geometry), geometry, band="wind", scale=100
    )
    calm_fraction = round(calm_km2 / water_km2, 2) if water_km2 else 0

    url = common.tile_url(
        wind,
        {
            "palette": ["#1E3A5F", "#1E6FE8", "#00BFA8", "#E8E36A", "#E8541E"],
            "min": 0,
            "max": 25,
        },
    )

    return {
        "tile_url": url,
        "result_image": wind,
        "mean_wind_ms": mean_wind,
        "max_wind_ms": max_wind,
        "calm_water_fraction": calm_fraction,
        "confidence": round(min(0.8, 0.55 + 0.03 * image_count), 2),
        "data_date": common.latest_image_date(period),
        "images_used": image_count,
        "headline_stat": {
            "label": "Mean ocean wind (proxy)",
            "value": mean_wind,
            "unit": "m/s",
        },
    }
