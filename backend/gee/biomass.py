"""
Forest Biomass & Structure — a genuine multi-sensor fusion.

Sentinel-1's C-band radar bounces off the top of a canopy, so it is poor at
biomass. This analysis instead uses ALOS PALSAR, an L-band SAR whose longer
wavelength penetrates into the canopy and scatters off trunks and branches, so
its cross-polarized (HV) return rises with woody above-ground biomass. That is
the physical basis of every spaceborne biomass map.

The fusion: L-band HV alone can be fooled by rough or urban surfaces that are
also bright. So we mask the biomass estimate to pixels that Sentinel-2 optical
confirms are actually live vegetation (NDVI above a threshold). Radar gives the
structure, optical vouches that it is really forest. Neither sensor alone does
this well; together they do.

Honesty: the tonnes-per-hectare figure is a rough, saturating proxy from HV
backscatter, not a calibrated inventory. L-band saturates over very dense
tropical forest, so this under-reads the highest biomass.

Data sources:
    JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH   L-band SAR annual mosaic, 25 m (HH, HV)
    COPERNICUS/S2_SR_HARMONIZED         optical, for the NDVI vegetation mask
"""

import ee
from datetime import datetime

from gee import common

PALSAR = "JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH"
S2 = "COPERNICUS/S2_SR_HARMONIZED"

# NDVI above this counts as live vegetation for the fusion mask.
_NDVI_VEG = 0.3
# Green -> dark-green biomass ramp (Mg/ha).
BIOMASS_PALETTE = ["#E8EFE9", "#7BC043", "#2E8B3D", "#0B3D18"]


def _palsar_hv_db(image: ee.Image) -> ee.Image:
    """PALSAR yearly-mosaic DN -> gamma-nought dB (JAXA calibration)."""
    # gamma0 [dB] = 10 * log10(DN^2) - 83.0
    dn = image.select("HV")
    return dn.pow(2).log10().multiply(10).subtract(83.0).rename("hv_db")


def estimate_biomass(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the PALSAR mosaic year is picked
            from end_date; Sentinel-2 NDVI is taken from the same window.

    Returns:
        tile_url, result_image, estimated_agb_mg_ha (mean over forest),
        forest_area_km2, mean_hv_db, ndvi_mean, confidence, data_date

    Raises:
        ValueError: if no PALSAR mosaic is available for the AOI/year.
    """
    geometry = common.bbox_geometry(bbox)
    year = datetime.strptime(end_date, "%Y-%m-%d").year

    # PALSAR yearly mosaics are annual; take the closest available epoch <= year.
    coll = (
        ee.ImageCollection(PALSAR)
        .filterBounds(geometry)
        .filterDate("2015-01-01", f"{year}-12-31")
        .sort("system:time_start", False)
    )
    if coll.size().getInfo() == 0:
        raise ValueError(
            "No ALOS PALSAR L-band mosaic is available for this area and year. "
            "PALSAR annual mosaics run from 2015; try an end date in that range."
        )
    palsar = ee.Image(coll.first())
    epoch_year = ee.Date(palsar.get("system:time_start")).format("YYYY").getInfo()

    hv_db = _palsar_hv_db(palsar)

    # Rough saturating AGB proxy (Mg/ha) from HV gamma0. Monotonic, saturates
    # near ~150 Mg/ha the way L-band does. Labelled approximate on purpose.
    agb = (
        hv_db.add(25).max(0).multiply(9.0).min(300).rename("agb")
    )

    # --- Fusion mask: Sentinel-2 confirms live vegetation ---
    s2 = (
        ee.ImageCollection(S2)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    have_optical = s2.size().getInfo() > 0
    if have_optical:
        best = ee.Image(s2.first())
        ndvi = best.normalizedDifference(["B8", "B4"]).rename("ndvi")
        veg_mask = ndvi.gt(_NDVI_VEG)
        ndvi_mean = ndvi.updateMask(veg_mask).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=30,
            maxPixels=1e10, bestEffort=True,
        ).get("ndvi").getInfo()
    else:
        # No cloud-free optical: fall back to a radar-only forest mask so the
        # analysis still returns, but say so in the confidence.
        veg_mask = hv_db.gt(-18)
        ndvi_mean = None

    forest_agb = agb.updateMask(veg_mask).clip(geometry)

    url = common.tile_url(
        forest_agb, {"min": 0, "max": 250, "palette": BIOMASS_PALETTE}
    )

    stats = forest_agb.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geometry, scale=30,
        maxPixels=1e10, bestEffort=True,
    ).getInfo()
    mean_agb = round(float(stats.get("agb") or 0), 1)

    mean_hv = hv_db.updateMask(veg_mask).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geometry, scale=30,
        maxPixels=1e10, bestEffort=True,
    ).get("hv_db").getInfo()

    forest_km2 = common.area_km2(
        veg_mask.selfMask().rename("agb").clip(geometry), geometry,
        band="agb", scale=30,
    )

    return {
        "tile_url": url,
        "result_image": forest_agb,
        "estimated_agb_mg_ha": mean_agb,
        "forest_area_km2": forest_km2,
        "mean_hv_db": round(float(mean_hv), 1) if mean_hv is not None else None,
        "ndvi_mean": round(float(ndvi_mean), 2) if ndvi_mean is not None else None,
        "optical_fusion": have_optical,
        "confidence": 0.75 if have_optical else 0.6,
        "data_date": f"{epoch_year}-12-31",
        "headline_stat": {
            "label": "Mean above-ground biomass",
            "value": mean_agb,
            "unit": "Mg/ha (approx)",
        },
    }
