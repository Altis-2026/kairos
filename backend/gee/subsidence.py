import ee

from gee import common

_SLOPE_THRESHOLD = 1.5
_DISPERSION_MAX = 0.42
_MIN_CORRELATION = 0.5
SUBSIDENCE_PALETTE = ["#1E6FE8", "#9BC7FF", "#0B120E", "#FFC59B", "#FF3B5C"]


def detect_subsidence(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV").filterDate(start_date, end_date)
    count = common.require_images(s1, f"this area between {start_date} and {end_date}")
    if count < 5:
        raise ValueError(
            "A subsidence trend needs at least ~5 Sentinel-1 passes to be "
            "meaningful. Widen the date range (several months works best)."
        )

    base = ee.Date(start_date)

    def add_time(img):
        t = ee.Image(img.date().difference(base, "year")).float().rename("t")
        return img.addBands(t)

    timed = s1.map(add_time).select(["t", "VV"])

    fitted = timed.reduce(ee.Reducer.linearFit())
    slope = fitted.select("scale")

    def to_amplitude(img):
        return (
            ee.Image(10)
            .pow(img.select("VV").divide(10))
            .sqrt()
            .rename("amp")
            .copyProperties(img, ["system:time_start"])
        )

    amp = s1.map(to_amplitude)
    amp_mean = amp.mean()
    amp_std = amp.reduce(ee.Reducer.stdDev())
    dispersion = amp_std.divide(amp_mean)
    stable = dispersion.lt(_DISPERSION_MAX)

    correlation = timed.reduce(ee.Reducer.pearsonsCorrelation()).select("correlation")
    consistent = correlation.abs().gte(_MIN_CORRELATION)

    permanent = common.permanent_water_mask(50)
    significant = slope.abs().gt(_SLOPE_THRESHOLD).And(stable).And(consistent).And(permanent.Not())
    trend = slope.updateMask(significant).rename("VV").clip(geometry)

    url = common.tile_url(trend, {"min": -4, "max": 4, "palette": SUBSIDENCE_PALETTE})

    trend_mask = significant.selfMask().rename("VV").clip(geometry)
    trend_km2 = common.area_km2(trend_mask, geometry, band="VV", scale=30)
    stable_mask = stable.And(permanent.Not()).selfMask().rename("VV").clip(geometry)
    stable_km2 = common.area_km2(stable_mask, geometry, band="VV", scale=90)

    data_date = common.latest_image_date(s1)
    confidence = round(min(0.90, 0.55 + 0.025 * count), 2)

    return {
        "tile_url": url,
        "result_image": trend_mask,
        "trend_area_km2": trend_km2,
        "stable_scatterer_km2": stable_km2,
        "confidence": confidence,
        "data_date": data_date,
        "images_used": count,
        "method_note": (
            "Amplitude trend screened by persistent-scatterer stability "
            "(dispersion < 0.42) and temporal consistency (|r| >= 0.5). "
            "Candidate zones for InSAR follow-up, not mm displacement."
        ),
        "headline_stat": {
            "label": "Progressive-change area",
            "value": trend_km2,
            "unit": "km²",
        },
    }
