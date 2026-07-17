"""
Flooded Forest / Mangrove Inundation.

Open-water flood mapping (gee/flood.py) goes dark where water is smooth — but
water standing UNDER trees does the opposite. The flooded trunk-water geometry
forms a corner reflector, so co-polarized backscatter rises sharply
(double-bounce). That brightening inside forest is invisible to optical
sensors, which only see canopy: this is a capability SAR alone has.

Method: within tree-covered pixels (ESA WorldCover classes 10 trees and 95
mangroves), flag a VV rise of more than +3 dB against a pre-window baseline.
Permanent wetlands flagged historically by JRC seasonal water are kept —
what matters is change against this window's own baseline.

Data sources: Sentinel-1 GRD (IW, VV), ESA WorldCover v200.
"""

from gee import common, fusion

import ee

WORLDCOVER = "ESA/WorldCover/v200"
_TREES, _MANGROVES = 10, 95
_DOUBLE_BOUNCE_DB = 3.0


def detect_flooded_forest(bbox: list, start_date: str, end_date: str) -> dict:
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
    base_start, base_end = common.baseline_window(start_date, days=60)
    baseline = s1.filterDate(base_start, base_end)
    baseline_count = common.require_images(baseline, "the 60-day pre-window baseline")

    diff = common.despeckle(current.mean()).subtract(
        common.despeckle(baseline.mean())
    )

    landcover = ee.ImageCollection(WORLDCOVER).first().select("Map")
    forest = landcover.eq(_TREES).Or(landcover.eq(_MANGROVES))

    flooded = (
        diff.gt(_DOUBLE_BOUNCE_DB)
        .And(forest)
        .where(common.permanent_water_mask(75), 0)
        .selfMask()
        .clip(geometry)
    )

    url = common.tile_url(flooded, {"palette": ["#00BFA8"], "min": 0, "max": 1})
    flooded_km2 = common.area_km2(flooded, geometry, band="VV", scale=30)
    forest_km2 = common.area_km2(
        forest.selfMask().clip(geometry), geometry, band="Map", scale=100
    )
    if forest_km2 < 1:
        raise ValueError(
            "This area has almost no tree cover, so flooded-forest detection "
            "does not apply. Try a forested floodplain, swamp or mangrove coast "
            "— or use Flood Extent Mapping for open-water flooding."
        )

    # Ensemble across nearby thresholds — brightening that survives ±0.5 dB is real.
    ens = common.ensemble_area(
        diff.updateMask(forest),
        [_DOUBLE_BOUNCE_DB - 0.5, _DOUBLE_BOUNCE_DB, _DOUBLE_BOUNCE_DB + 0.5],
        geometry,
        band="VV",
        direction="gt",
    )
    confidence = round(
        min(0.9, 0.6 + 0.02 * current_count) - common.spread_penalty(
            ens["relative_spread"]
        ),
        2,
    )

    result = {
        "tile_url": url,
        "result_image": flooded,
        "flooded_forest_km2": flooded_km2,
        "flooded_forest_low_km2": ens["area_low_km2"],
        "flooded_forest_high_km2": ens["area_high_km2"],
        "forest_area_km2": forest_km2,
        "confidence": confidence,
        "data_date": common.latest_image_date(current),
        "current_images_used": current_count,
        "baseline_images_used": baseline_count,
        "method_note": (
            "Double-bounce brightening (VV rise > +3 dB vs a 60-day baseline) "
            "inside WorldCover tree/mangrove pixels. Optical sensors cannot see "
            "under canopy; expect little or no optical confirmation here."
        ),
        "headline_stat": {
            "label": "Flooded forest",
            "value": flooded_km2,
            "unit": "km²",
        },
    }

    # Optical is expected to miss sub-canopy water — reported for honesty, and
    # low agreement is NOT penalized (that asymmetry is the point of SAR here).
    try:
        result.update(
            fusion.confirm_water(flooded, geometry, start_date, end_date)
        )
    except Exception:
        result["optical_confirmation"] = None
    return result
