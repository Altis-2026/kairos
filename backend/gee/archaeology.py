import ee

from gee import common

PALSAR = "JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH"
WORLDCOVER = "ESA/WorldCover/v200"
_SIGMA = 2.0


def _to_gamma0_db(image: ee.Image, band: str) -> ee.Image:
    dn = image.select(band).toFloat()
    return dn.pow(2).log10().multiply(10).subtract(83.0)


def detect_anomalies(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    year = int(end_date[:4])

    coll = (
        ee.ImageCollection(PALSAR)
        .filterBounds(geometry)
        .filter(ee.Filter.calendarRange(2015, year, "year"))
        .sort("system:time_start", False)
    )
    if coll.size().getInfo() == 0:
        raise ValueError(
            "No ALOS PALSAR L-band mosaic is available for this area and year. "
            "PALSAR annual mosaics run from 2015; try an end date in that range."
        )
    mosaic = ee.Image(coll.first())
    epoch_year = ee.Date(mosaic.get("system:time_start")).format("YYYY").getInfo()

    hv = _to_gamma0_db(mosaic, "HV")

    local_median = hv.focalMedian(250, "circle", "meters")
    local_dev = hv.subtract(local_median).abs()
    local_scale = local_dev.focalMedian(250, "circle", "meters").max(0.25)
    zscore = hv.subtract(local_median).divide(local_scale)

    landcover = ee.ImageCollection(WORLDCOVER).first().select("Map")
    keep = landcover.neq(50).And(landcover.neq(80))
    anomalies = (
        zscore.abs().gt(_SIGMA).And(keep).where(common.permanent_water_mask(50), 0).selfMask().clip(geometry)
    )

    url = common.tile_url(anomalies, {"palette": ["#E8A318"], "min": 0, "max": 1})
    anomaly_km2 = common.area_km2(anomalies, geometry, band="HV", scale=25)

    return {
        "tile_url": url,
        "result_image": anomalies,
        "anomaly_km2": anomaly_km2,
        "palsar_epoch": epoch_year,
        "confidence": 0.5,
        "data_date": f"{epoch_year}-12-31",
        "method_note": (
            "L-band (ALOS PALSAR) HV texture anomalies >2 sigma from the 250 m "
            "neighbourhood, with cities and water masked. L-band penetrates dry "
            "sand and canopy, so buried/obscured structure can surface here, "
            "but so do modern field boundaries, tracks and pipelines. These are "
            "CANDIDATE targets for ground survey, not discoveries."
        ),
        "headline_stat": {
            "label": "Anomaly area",
            "value": anomaly_km2,
            "unit": "km²",
        },
    }
