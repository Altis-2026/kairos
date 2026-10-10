from datetime import datetime

import ee

from gee import common

PALSAR = "JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH"
S2 = "COPERNICUS/S2_SR_HARMONIZED"

_NDVI_VEG = 0.3
BIOMASS_PALETTE = ["#E8EFE9", "#7BC043", "#2E8B3D", "#0B3D18"]


def _palsar_hv_db(image: ee.Image) -> ee.Image:
    dn = image.select("HV")
    return dn.pow(2).log10().multiply(10).subtract(83.0).rename("hv_db")


def estimate_biomass(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    year = datetime.strptime(end_date, "%Y-%m-%d").year

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

    agb = hv_db.add(25).max(0).multiply(9.0).min(300).rename("agb")

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
        ndvi_mean = (
            ndvi.updateMask(veg_mask)
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=30,
                maxPixels=1e10,
                bestEffort=True,
            )
            .get("ndvi")
            .getInfo()
        )
    else:
        veg_mask = hv_db.gt(-18)
        ndvi_mean = None

    forest_agb = agb.updateMask(veg_mask).clip(geometry)

    url = common.tile_url(forest_agb, {"min": 0, "max": 250, "palette": BIOMASS_PALETTE})

    stats = forest_agb.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=30,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_agb = round(float(stats.get("agb") or 0), 1)

    mean_hv = (
        hv_db.updateMask(veg_mask)
        .reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=30,
            maxPixels=1e10,
            bestEffort=True,
        )
        .get("hv_db")
        .getInfo()
    )

    forest_km2 = common.area_km2(
        veg_mask.selfMask().rename("agb").clip(geometry),
        geometry,
        band="agb",
        scale=30,
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
