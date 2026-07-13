"""
Land Subsidence Indicator (persistent-scatterer-screened amplitude trend).

Cities built on drained wetlands or over-pumped aquifers — Jakarta, Mexico City,
parts of the US Central Valley — are slowly sinking, sometimes tens of cm per
year. Millimetre-precise vertical motion needs InSAR *phase*, which Sentinel-1
GRD does not carry. So, honestly, this is not an InSAR displacement map.

What it *is*: a long-baseline temporal-trend detector, hardened with the same
screening real PSInSAR pipelines use to pick their measurement points:

1. Trend — ordinary least-squares slope of each pixel's VV backscatter through
   time (dB/year). Progressive subsidence, cracking or reworking shows a
   persistent directional drift that seasonal noise does not.
2. Stability — the amplitude dispersion index D_A = sigma/mu of the pixel's
   linear amplitude time series (Ferretti et al. 2001). D_A below ~0.42 marks
   a persistent scatterer: a target stable enough that its trend is physical
   rather than speckle. This is literally the PSInSAR candidate-selection
   metric, applied to the amplitude data GRD actually carries.
3. Consistency — Pearson correlation of backscatter against time. A steep
   slope produced by one outlier scene has low |r|; genuine monotonic drift
   has high |r|. We require |r| >= 0.5.

A pixel is flagged only when all three hold, over stable (non-water) land —
surfacing candidate zones of progressive change for follow-up with a proper
InSAR study.

Data source: Sentinel-1 GRD (IW, VV) time series.
"""

import ee
from gee import common

# A pixel's |trend| must exceed this (dB/year) to count as progressive change.
_SLOPE_THRESHOLD = 1.5
# Amplitude dispersion below this marks a persistent-scatterer candidate.
_DISPERSION_MAX = 0.42
# Minimum |Pearson r| between time and backscatter for a consistent trend.
_MIN_CORRELATION = 0.5
# Diverging palette: blue = falling return (often sinking/wetting), red = rising.
SUBSIDENCE_PALETTE = ["#1E6FE8", "#9BC7FF", "#0B120E", "#FFC59B", "#FF3B5C"]


def detect_subsidence(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the full window to fit a trend over.
            A longer window (many months) gives a far more reliable trend.

    Returns:
        tile_url, result_image, trend_area_km2, stable_scatterer_km2,
        confidence, data_date, images_used, headline_stat

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

    timed = s1.map(add_time).select(["t", "VV"])

    # 1. Trend: linearFit expects [x (time), y (backscatter)].
    fitted = timed.reduce(ee.Reducer.linearFit())
    slope = fitted.select("scale")  # dB per year

    # 2. Stability: amplitude dispersion on the LINEAR amplitude stack.
    #    GRD dB -> linear power (10^(dB/10)) -> amplitude (sqrt).
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

    # 3. Consistency: |Pearson r| of backscatter vs time.
    correlation = timed.reduce(ee.Reducer.pearsonsCorrelation()).select(
        "correlation"
    )
    consistent = correlation.abs().gte(_MIN_CORRELATION)

    # Flag only where all three screens pass, over non-water land.
    permanent = common.permanent_water_mask(50)
    significant = (
        slope.abs()
        .gt(_SLOPE_THRESHOLD)
        .And(stable)
        .And(consistent)
        .And(permanent.Not())
    )
    trend = slope.updateMask(significant).rename("VV").clip(geometry)

    url = common.tile_url(
        trend, {"min": -4, "max": 4, "palette": SUBSIDENCE_PALETTE}
    )

    # Areas: flagged trend, and total persistent-scatterer ground for context.
    trend_mask = significant.selfMask().rename("VV").clip(geometry)
    trend_km2 = common.area_km2(trend_mask, geometry, band="VV", scale=30)
    stable_mask = (
        stable.And(permanent.Not()).selfMask().rename("VV").clip(geometry)
    )
    stable_km2 = common.area_km2(stable_mask, geometry, band="VV", scale=90)

    data_date = common.latest_image_date(s1)
    # Triple screening removes most speckle-driven false trends, so confidence
    # can start higher than the raw-slope version did; passes still help.
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
