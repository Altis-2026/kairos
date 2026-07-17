"""
Signal time-series extraction — the researcher's bread and butter.

Every remote-sensing paper's Figure 3 is "the signal over our site through
time". This pulls a per-scene mean of a chosen variable over the AOI across
the whole requested range, in ONE Earth Engine round trip (map + getInfo on a
FeatureCollection), so the caller gets plain (date, value) points ready for a
chart, a CSV, and trend statistics.

Variables:
    VV, VH      Sentinel-1 backscatter (dB) — all-weather, every ~6-12 days
    NDVI        vegetation vigour   (optical)
    NDWI        open-water index    (optical)
    NDSI        snow index          (optical)

Optical sources:
    S2          Sentinel-2 SR + Cloud Score+ masking (10-20 m, ~5-day revisit)
    HLS         NASA Harmonized Landsat (HLSL30 v2, 30 m) — deepens the archive
                and adds Landsat's cadence; masked with its Fmask band.

Per-scene cloud masking means a cloudy scene contributes nothing rather than
poisoning the series; fully-masked scenes drop out as nulls.
"""

import ee
from gee import common

S2 = "COPERNICUS/S2_SR_HARMONIZED"
CS_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
HLS_L30 = "NASA/HLS/HLSL30/v002"

SAR_VARIABLES = ("VV", "VH")
OPTICAL_VARIABLES = ("NDVI", "NDWI", "NDSI")

# Index -> (band_a, band_b) per source, normalizedDifference(a, b).
_S2_BANDS = {"NDVI": ("B8", "B4"), "NDWI": ("B3", "B8"), "NDSI": ("B3", "B11")}
_HLS_BANDS = {"NDVI": ("B5", "B4"), "NDWI": ("B3", "B5"), "NDSI": ("B3", "B6")}

_UNITS = {"VV": "dB", "VH": "dB", "NDVI": "index", "NDWI": "index", "NDSI": "index"}


def _collect(points_fc: ee.FeatureCollection) -> list:
    """One getInfo round trip; drop nulls; sort by date."""
    raw = points_fc.getInfo().get("features", [])
    pts = []
    for f in raw:
        p = f.get("properties", {})
        if p.get("value") is None:
            continue
        pts.append({"date": p["date"], "value": round(float(p["value"]), 4)})
    pts.sort(key=lambda x: x["date"])
    return pts


def _sar_series(geometry, start_date, end_date, variable) -> list:
    coll = common.s1_collection(geometry, polarization=variable).filterDate(
        start_date, end_date
    )
    common.require_images(coll, f"this area between {start_date} and {end_date}")

    def per_image(img):
        mean = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=100,
            maxPixels=1e9,
            bestEffort=True,
        ).get(variable)
        return ee.Feature(
            None,
            {"date": img.date().format("YYYY-MM-dd"), "value": mean},
        )

    return _collect(ee.FeatureCollection(coll.map(per_image)))


def _s2_series(geometry, start_date, end_date, variable) -> list:
    a, b = _S2_BANDS[variable]
    coll = (
        ee.ImageCollection(S2)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .linkCollection(ee.ImageCollection(CS_PLUS), ["cs"])
    )
    if coll.size().getInfo() == 0:
        raise ValueError(
            f"No Sentinel-2 scenes over this area between {start_date} and "
            f"{end_date}."
        )

    def per_image(img):
        clear = img.select("cs").gte(0.6)
        index = img.updateMask(clear).normalizedDifference([a, b])
        mean = index.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=60,
            maxPixels=1e9,
            bestEffort=True,
        ).get("nd")
        return ee.Feature(
            None, {"date": img.date().format("YYYY-MM-dd"), "value": mean}
        )

    return _collect(ee.FeatureCollection(coll.map(per_image)))


def _hls_series(geometry, start_date, end_date, variable) -> list:
    a, b = _HLS_BANDS[variable]
    coll = (
        ee.ImageCollection(HLS_L30)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    if coll.size().getInfo() == 0:
        raise ValueError(
            f"No Harmonized Landsat (HLS) scenes over this area between "
            f"{start_date} and {end_date}. HLS v2 coverage starts in 2013."
        )

    def per_image(img):
        fmask = img.select("Fmask")
        # Bits: 0 cirrus, 1 cloud, 3 shadow -> all must be clear.
        clear = fmask.bitwiseAnd((1 << 0) | (1 << 1) | (1 << 3)).eq(0)
        index = img.updateMask(clear).normalizedDifference([a, b])
        mean = index.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=90,
            maxPixels=1e9,
            bestEffort=True,
        ).get("nd")
        return ee.Feature(
            None, {"date": img.date().format("YYYY-MM-dd"), "value": mean}
        )

    return _collect(ee.FeatureCollection(coll.map(per_image)))


def extract_series(
    bbox: list,
    start_date: str,
    end_date: str,
    variable: str = "VV",
    source: str = None,
) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD'
        variable: VV | VH | NDVI | NDWI | NDSI
        source: for optical variables, 'S2' (default) or 'HLS'
    Returns:
        {"points": [{date, value}...], "variable", "unit", "source", "count"}
    Raises:
        ValueError: unknown variable, or no data for the AOI/range
    """
    variable = variable.upper()
    geometry = common.bbox_geometry(bbox)

    if variable in SAR_VARIABLES:
        points = _sar_series(geometry, start_date, end_date, variable)
        src = "Sentinel-1"
    elif variable in OPTICAL_VARIABLES:
        if (source or "S2").upper() == "HLS":
            points = _hls_series(geometry, start_date, end_date, variable)
            src = "HLS (Landsat)"
        else:
            points = _s2_series(geometry, start_date, end_date, variable)
            src = "Sentinel-2"
    else:
        raise ValueError(
            f"Unknown variable '{variable}'. Choose from: "
            f"{', '.join(SAR_VARIABLES + OPTICAL_VARIABLES)}."
        )

    if len(points) < 3:
        raise ValueError(
            f"Only {len(points)} usable {variable} observations in this range "
            "— too few for a series. Widen the date range (clouds mask optical "
            "scenes; SAR revisit is 6-12 days)."
        )

    return {
        "points": points,
        "variable": variable,
        "unit": _UNITS[variable],
        "source": src,
        "count": len(points),
    }
