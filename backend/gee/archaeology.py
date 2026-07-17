"""
Archaeology Mode — L-band anomaly mapping under canopy and dry sand.

L-band microwaves (~24 cm, ALOS PALSAR) penetrate metres of very dry sand and
see through forest canopy to the ground surface — the property archaeologists
have used since SIR-A revealed buried Saharan paleochannels in 1982. Buried
walls, mounds, causeways and old river courses change ground roughness and
moisture retention, which shows up as backscatter TEXTURE anomalies: locally
coherent bright/dark structure that doesn't match the surrounding natural
pattern.

Honest framing (repeated in the method note): this produces CANDIDATE
anomalies for ground survey, not discoveries. Modern fields, roads and
pipelines produce identical signatures; archaeology begins, not ends, here.

Method: PALSAR yearly-mosaic HV (volume/roughness sensitive) is contrasted
against its own neighbourhood — a pixel's deviation from the 250 m local
median, normalized by the local spread — and pixels beyond 2 sigma are kept
as anomalies. HV is preferred over HH because surface double-bounce from
modern structures saturates HH first.

Data sources: JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH (L-band, 25 m), ESA WorldCover.
"""

import ee
from gee import common

PALSAR = "JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH"
WORLDCOVER = "ESA/WorldCover/v200"
_SIGMA = 2.0


def _to_gamma0_db(image: ee.Image, band: str) -> ee.Image:
    """PALSAR yearly-mosaic DN -> gamma-nought dB (JAXA calibration)."""
    dn = image.select(band).toFloat()
    return dn.pow(2).log10().multiply(10).subtract(83.0)


def detect_anomalies(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date: 'YYYY-MM-DD'
        end_date: 'YYYY-MM-DD'
    Returns:
        dict containing at minimum: tile_url (str), data_date (str)
    Raises:
        ValueError: if no satellite data is available for the given bbox/dates
    """
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

    # Local anomaly: deviation from the 250 m neighbourhood median, scaled by
    # the neighbourhood's own spread so uniform desert and busy forest are
    # judged by their own textures.
    local_median = hv.focalMedian(250, "circle", "meters")
    local_dev = hv.subtract(local_median).abs()
    local_scale = local_dev.focalMedian(250, "circle", "meters").max(0.25)
    zscore = hv.subtract(local_median).divide(local_scale)

    # Keep strong structured anomalies; drop water and dense built-up areas
    # (modern cities are wall-to-wall "anomalies" and would drown the map).
    landcover = ee.ImageCollection(WORLDCOVER).first().select("Map")
    keep = landcover.neq(50).And(landcover.neq(80))
    anomalies = (
        zscore.abs()
        .gt(_SIGMA)
        .And(keep)
        .where(common.permanent_water_mask(50), 0)
        .selfMask()
        .clip(geometry)
    )

    url = common.tile_url(anomalies, {"palette": ["#E8A318"], "min": 0, "max": 1})
    anomaly_km2 = common.area_km2(anomalies, geometry, band="HV", scale=25)

    return {
        "tile_url": url,
        "result_image": anomalies,
        "anomaly_km2": anomaly_km2,
        "palsar_epoch": epoch_year,
        "confidence": 0.5,  # candidates for survey, deliberately modest
        "data_date": f"{epoch_year}-12-31",
        "method_note": (
            "L-band (ALOS PALSAR) HV texture anomalies >2 sigma from the 250 m "
            "neighbourhood, with cities and water masked. L-band penetrates dry "
            "sand and canopy, so buried/obscured structure can surface here — "
            "but so do modern field boundaries, tracks and pipelines. These are "
            "CANDIDATE targets for ground survey, not discoveries."
        ),
        "headline_stat": {
            "label": "Anomaly area",
            "value": anomaly_km2,
            "unit": "km²",
        },
    }
