from gee import common


def detect_sea_ice(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="HH", instrument_mode="EW")

    period = s1.filterDate(start_date, end_date)
    image_count = common.require_images(
        period,
        f"this polar area between {start_date} and {end_date} "
        "(sea ice mapping requires EW-mode data, which ESA only acquires over polar regions)",
    )

    composite = period.mean()

    ice_mask = composite.gt(-18).selfMask().clip(geometry)

    url = common.tile_url(ice_mask, {"palette": ["#BFEFFF"], "min": 0, "max": 1})
    ice_km2 = common.area_km2(ice_mask, geometry, band="HH", scale=100)
    data_date = common.latest_image_date(period)

    return {
        "tile_url": url,
        "result_image": ice_mask,
        "ice_extent_km2": ice_km2,
        "confidence": 0.88,
        "data_date": data_date,
        "images_used": image_count,
        "headline_stat": {"label": "Sea ice extent", "value": ice_km2, "unit": "km²"},
    }
