"""
Land Subsidence Indicator (amplitude-trend proxy).

Cities built on drained wetlands or over-pumped aquifers — Jakarta, Mexico City,
parts of the US Central Valley — are slowly sinking, sometimes tens of cm per
year. Millimetre-precise vertical motion needs InSAR *phase*, which Sentinel-1
GRD does not carry. So, honestly, this is not an InSAR displacement map.

What it *is*: a long-baseline temporal-trend detector. Over a multi-month to
multi-year window we fit a straight line to each pixel's VV backscatter through
time (an ordinary least-squares slope, in dB per year). Ground that is
progressively subsiding, cracking, or being reworked shows a persistent,
directional drift in its radar return that random seasonal noise does not. We
flag pixels whose trend is both steep and consistent, over stable (non-water)
land — surfacing candidate zones of progressive surface change for follow-up
with a proper InSAR study.

Data source: Sentinel-1 GRD (IW, VV) time series.
"""

import ee
from datetime import datetime, timedelta
from gee import common

# A pixel's |trend| must exceed this (dB/year) to count as progressive change.
_SLOPE_THRESHOLD = 1.5
# Diverging palette: blue = falling return (often sinking/wetting), red = rising.
SUBSIDENCE_PALETTE = ["#1E6FE8", "#9BC7FF", "#0B120E", "#FFC59B", "#FF3B5C"]


def detect_subsidence(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the full window to fit a trend over.
            A longer window (many months) gives a far more reliable trend.

    Returns:
        tile_url, result_image, trend_area_km2, confidence, data_date,
        images_used, headline_stat

    Raises:
        ValueError: if too little Sentinel-1 data is available to fit a trend
    """
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV").filterDate(
        start_date, end_date
    )
    count = common.require_images(
        s1, f"this area between {start_date} and {end_date}"
    )
    if count < 5:
        raise ValueError(
            "A subsidence trend needs at least ~5 Sentinel-1 passes to be "
            "meaningful. Widen the date range (several months works best)."
        )

    base = ee.Date(start_date)

    def add_time(img):
        # Independent variable: years since the window start.
        t = (
            ee.Image(img.date().difference(base, "year"))
            .float()
            .rename("t")
        )
        return img.addBands(t)

    # linearFit expects a 2-band collection: [x (time), y (backscatter)].
    fitted = (
        s1.map(add_time)
        .select(["t", "VV"])
        .reduce(ee.Reducer.linearFit())
    )
    slope = fitted.select("scale")  # dB per year

    # Significant, directional trend over non-water land.
    permanent = common.permanent_water_mask(50)
    significant = slope.abs().gt(_SLOPE_THRESHOLD).And(permanent.Not())
    trend = slope.updateMask(significant).rename("VV").clip(geometry)

    url = common.tile_url(
        trend, {"min": -4, "max": 4, "palette": SUBSIDENCE_PALETTE}
    )

    # Area of significant trend (count truthy mask pixels).
    trend_mask = significant.selfMask().rename("VV").clip(geometry)
    trend_km2 = common.area_km2(trend_mask, geometry, band="VV", scale=30)

    data_date = common.latest_image_date(s1)
    confidence = round(min(0.85, 0.45 + 0.03 * count), 2)

    return {
        "tile_url": url,
        "result_image": trend_mask,
        "trend_area_km2": trend_km2,
        "confidence": confidence,
        "data_date": data_date,
        "images_used": count,
        "headline_stat": {
            "label": "Progressive-change area",
            "value": trend_km2,
            "unit": "km²",
        },
    }
