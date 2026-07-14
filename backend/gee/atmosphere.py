"""
Atmospheric composition from Sentinel-5P (TROPOMI).

A completely different modality from Kairos's radar work: instead of surface
backscatter, TROPOMI measures trace gases in the atmospheric column. Two
analyses that broaden Kairos well beyond disaster/land use:

  detect_methane        CH4 column (a hot climate-monitoring frontier: oil and
                        gas leaks, landfills, wetlands)
  monitor_air_quality   NO2 column (combustion: traffic, power plants, cities)

TROPOMI is coarse (~7 km) and column-integrated (it sees the whole vertical
column, not ground concentration), so these map relative enhancements and
regional patterns, not a smokestack. Both average all valid retrievals in the
window to beat down noise and cloud gaps.

Data sources:
    COPERNICUS/S5P/OFFL/L3_CH4   methane column mixing ratio (ppb)
    COPERNICUS/S5P/OFFL/L3_NO2   tropospheric NO2 column (mol/m^2)
"""

import ee

from gee import common

S5P_CH4 = "COPERNICUS/S5P/OFFL/L3_CH4"
S5P_NO2 = "COPERNICUS/S5P/OFFL/L3_NO2"

CH4_BAND = "CH4_column_volume_mixing_ratio_dry_air"
NO2_BAND = "tropospheric_NO2_column_number_density"

# Sequential ramps (low -> high).
METHANE_PALETTE = ["#0B3D91", "#1E6FE8", "#00BFA8", "#E8A318", "#FF3B5C"]
NO2_PALETTE = ["#0B120E", "#3BA7FF", "#7BC043", "#E8A318", "#FF3B5C"]


def _require(coll: ee.ImageCollection, gas: str, start, end):
    n = coll.size().getInfo()
    if n == 0:
        raise ValueError(
            f"No Sentinel-5P {gas} retrievals for this area between {start} and "
            f"{end}. TROPOMI has daily global coverage from 2018; widen the "
            "window (cloud and quality filtering can thin out short spans)."
        )
    return n


def detect_methane(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Mean methane column over the window, with the enhancement zones (pixels
    well above the local mean) flagged — candidate emission areas.

    Returns: tile_url, mean_ch4_ppb, enhancement_area_km2, confidence, data_date
    """
    geometry = common.bbox_geometry(bbox)
    coll = (
        ee.ImageCollection(S5P_CH4)
        .select(CH4_BAND)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    count = _require(coll, "methane", start_date, end_date)

    mean_img = coll.mean().rename("ch4").clip(geometry)

    stats = mean_img.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=geometry, scale=7000, maxPixels=1e10, bestEffort=True,
    ).getInfo()
    mean_ch4 = stats.get("ch4_mean")
    std_ch4 = stats.get("ch4_stdDev") or 0

    # Enhancement: column more than 1.5 sigma above the local mean.
    threshold = ee.Number(mean_ch4).add(ee.Number(std_ch4).multiply(1.5))
    enhanced = mean_img.gt(ee.Image.constant(threshold)).selfMask().rename("ch4")
    enh_km2 = common.area_km2(enhanced.clip(geometry), geometry, band="ch4", scale=7000)

    vmin = (mean_ch4 or 1850) - 40
    vmax = (mean_ch4 or 1850) + 60
    url = common.tile_url(
        mean_img, {"min": vmin, "max": vmax, "palette": METHANE_PALETTE}
    )

    return {
        "tile_url": url,
        "result_image": enhanced.clip(geometry),
        "mean_ch4_ppb": round(float(mean_ch4), 1) if mean_ch4 is not None else None,
        "enhancement_area_km2": enh_km2,
        "retrievals_used": count,
        "confidence": 0.7,
        "data_date": common.latest_image_date(coll),
        "headline_stat": {
            "label": "Mean methane column",
            "value": round(float(mean_ch4), 1) if mean_ch4 is not None else 0,
            "unit": "ppb",
        },
    }


def monitor_air_quality(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Mean tropospheric NO2 over the window, with pollution hotspots flagged.

    Returns: tile_url, mean_no2, hotspot_area_km2, confidence, data_date
    """
    geometry = common.bbox_geometry(bbox)
    coll = (
        ee.ImageCollection(S5P_NO2)
        .select(NO2_BAND)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    count = _require(coll, "NO2", start_date, end_date)

    mean_img = coll.mean().rename("no2").clip(geometry)

    stats = mean_img.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=geometry, scale=7000, maxPixels=1e10, bestEffort=True,
    ).getInfo()
    mean_no2 = stats.get("no2_mean")
    std_no2 = stats.get("no2_stdDev") or 0

    threshold = ee.Number(mean_no2).add(ee.Number(std_no2).multiply(1.5))
    hotspot = mean_img.gt(ee.Image.constant(threshold)).selfMask().rename("no2")
    hot_km2 = common.area_km2(hotspot.clip(geometry), geometry, band="no2", scale=7000)

    # NO2 columns are small numbers (mol/m^2); scale a sensible display window.
    vmax = (mean_no2 or 0.0001) * 3
    url = common.tile_url(
        mean_img, {"min": 0, "max": vmax, "palette": NO2_PALETTE}
    )

    # mol/m^2 -> micromol/m^2 for a friendlier headline number.
    mean_umol = round(float(mean_no2) * 1e6, 1) if mean_no2 is not None else 0

    return {
        "tile_url": url,
        "result_image": hotspot.clip(geometry),
        "mean_no2_umol_m2": mean_umol,
        "hotspot_area_km2": hot_km2,
        "retrievals_used": count,
        "confidence": 0.72,
        "data_date": common.latest_image_date(coll),
        "headline_stat": {
            "label": "Mean tropospheric NO₂",
            "value": mean_umol,
            "unit": "µmol/m²",
        },
    }
