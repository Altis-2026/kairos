"""
Wet Snow Extent (melt mapping).

The honest version of "SAR snow monitoring": C-band cannot measure snow depth
or water equivalent (that needs L-band InSAR or passive microwave), but it is
excellent at one thing — telling WET snow from dry/no snow. Liquid water in
the snowpack absorbs the radar wave, so melting snow goes dark. The classic
Nagler & Rott method thresholds the ratio of the melt-season image against a
frozen reference at about -3 dB.

Reference window: same area, mid-winter before the window (frozen/dry snow or
bare frozen ground). Wet-snow pixels are where current backscatter sits more
than 3 dB below that reference, above 0 °C-isotherm-agnostic terrain — we
simply exclude permanent water and report the elevation band of the melt from
the Copernicus GLO-30 DEM.

Data sources: Sentinel-1 GRD (IW, VV), COPERNICUS/DEM/GLO30, JRC GSW.
"""

from datetime import datetime, timedelta

import ee
from gee import common, fusion

_DEM = "COPERNICUS/DEM/GLO30"
_WET_SNOW_DB = -3.0


def _winter_reference(start_date: str) -> tuple:
    """A 45-day frozen-reference window centred on the winter before start_date.

    Northern-hemisphere January; for southern-hemisphere AOIs July would be
    more correct, but the ratio method is robust as long as the reference is
    colder/drier than the analysis window — the method note says exactly what
    was used so the user can judge.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    jan15 = datetime(start_dt.year if start_dt.month >= 3 else start_dt.year - 1, 1, 15)
    if jan15 >= start_dt:
        jan15 = datetime(start_dt.year - 1, 1, 15)
    return (
        (jan15 - timedelta(days=22)).strftime("%Y-%m-%d"),
        (jan15 + timedelta(days=22)).strftime("%Y-%m-%d"),
    )


def detect_wet_snow(bbox: list, start_date: str, end_date: str) -> dict:
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
    s1 = common.s1_collection(geometry, polarization="VV")

    current = s1.filterDate(start_date, end_date)
    current_count = common.require_images(
        current, f"this area between {start_date} and {end_date}"
    )

    ref_start, ref_end = _winter_reference(start_date)
    reference = s1.filterDate(ref_start, ref_end)
    common.require_images(
        reference, f"the frozen reference window ({ref_start} to {ref_end})"
    )

    # dB difference = ratio in linear units; Nagler threshold at -3 dB.
    diff = common.despeckle(current.mean()).subtract(
        common.despeckle(reference.mean())
    )
    wet = (
        diff.lt(_WET_SNOW_DB)
        .where(common.permanent_water_mask(50), 0)
        .selfMask()
        .clip(geometry)
    )

    url = common.tile_url(wet, {"palette": ["#7FD8FF"], "min": 0, "max": 1})
    wet_km2 = common.area_km2(wet, geometry, band="VV", scale=30)

    # Elevation of the melt zone — the number a hydrologist actually wants.
    dem = ee.ImageCollection(_DEM).select("DEM").mosaic()
    elev = dem.updateMask(wet.unmask(0)).reduceRegion(
        reducer=ee.Reducer.percentile([10, 50, 90]),
        geometry=geometry,
        scale=90,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()

    ens = common.ensemble_area(
        diff, [-3.5, -3.0, -2.5], geometry, band="VV",
        exclude_mask=common.permanent_water_mask(50), direction="lt",
    )
    confidence = round(
        min(0.88, 0.6 + 0.02 * current_count)
        - common.spread_penalty(ens["relative_spread"]),
        2,
    )

    def _m(key):
        v = elev.get(key)
        return round(float(v)) if v is not None else None

    result = {
        "tile_url": url,
        "result_image": wet,
        "wet_snow_km2": wet_km2,
        "wet_snow_low_km2": ens["area_low_km2"],
        "wet_snow_high_km2": ens["area_high_km2"],
        "melt_elevation_median_m": _m("DEM_p50"),
        "melt_elevation_low_m": _m("DEM_p10"),
        "melt_elevation_high_m": _m("DEM_p90"),
        "reference_window": f"{ref_start} to {ref_end}",
        "confidence": confidence,
        "data_date": common.latest_image_date(current),
        "images_used": current_count,
        "method_note": (
            "Nagler ratio method: wet snow absorbs C-band, so pixels more than "
            "3 dB below the frozen mid-winter reference are melting snow. This "
            "maps wet-snow EXTENT — C-band cannot measure depth or snow water "
            "equivalent. Reference window assumes northern-hemisphere winter."
        ),
        "headline_stat": {"label": "Wet snow", "value": wet_km2, "unit": "km²"},
    }

    try:
        result.update(fusion.confirm_snow(wet, geometry, start_date, end_date))
    except Exception:
        result["optical_confirmation"] = None
    return result
