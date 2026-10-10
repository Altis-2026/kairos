import ee

from gee import common, fusion

_SAR_FLOOD_DB = -3.0
_MIN_OPTICAL_COVERAGE_PCT = 20.0

_CLASS_PALETTE = ["#E8A318", "#3BA7FF", "#00BFA8"]


def flood_consensus(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)

    s1 = common.s1_collection(geometry, polarization="VV")
    current = s1.filterDate(start_date, end_date)
    current_count = common.require_images(current, f"this area between {start_date} and {end_date}")
    base_start, base_end = common.baseline_window(start_date, days=30)
    baseline = s1.filterDate(base_start, base_end)
    common.require_images(baseline, "the 30-day pre-flood baseline")

    diff = common.despeckle(current.mean()).subtract(common.despeckle(baseline.mean()))
    permanent = common.permanent_water_mask(75)
    sar_water = diff.lt(_SAR_FLOOD_DB).where(permanent, 0).gt(0)

    try:
        composite = fusion._masked_composite(geometry, start_date, end_date)
    except ValueError:
        raise ValueError(
            "No usable Sentinel-2 optical view exists in this window, so a "
            "two-method consensus is not possible here. Run Flood Extent "
            "Mapping (SAR-only) instead. That is exactly what it is for."
        )
    ndwi = composite.normalizedDifference(["B3", "B8"])
    optical_water = ndwi.gt(0).where(permanent, 0).unmask(0).gt(0)
    optical_valid = composite.select("B3").mask()

    aoi_m2 = geometry.area(maxError=100).getInfo()
    valid_m2 = float(
        optical_valid.multiply(ee.Image.pixelArea())
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=20,
            maxPixels=1e10,
            bestEffort=True,
        )
        .getInfo()
        .get("B3", 0)
        or 0
    )
    coverage_pct = round(100 * valid_m2 / aoi_m2, 1) if aoi_m2 else 0.0
    if coverage_pct < _MIN_OPTICAL_COVERAGE_PCT:
        raise ValueError(
            f"Cloud-free optical covers only {coverage_pct}% of this area in "
            "the window, too little for an honest consensus. Run Flood Extent "
            "Mapping (SAR-only) instead."
        )

    sar = sar_water.updateMask(optical_valid).rename("cls")
    opt = optical_water.updateMask(optical_valid)
    classes = sar.multiply(1).add(opt.multiply(2)).updateMask(sar.Or(opt)).clip(geometry)

    url = common.tile_url(classes, {"palette": _CLASS_PALETTE, "min": 1, "max": 3})

    areas = {}
    for cls, key in ((1, "sar_only"), (2, "optical_only"), (3, "consensus")):
        areas[key] = common.area_km2(classes.eq(cls).selfMask(), geometry, band="cls", scale=30)
    union = areas["sar_only"] + areas["optical_only"] + areas["consensus"]
    agreement_pct = round(100 * areas["consensus"] / union, 1) if union > 0 else None

    return {
        "tile_url": url,
        "result_image": classes,
        "consensus_km2": areas["consensus"],
        "sar_only_km2": areas["sar_only"],
        "optical_only_km2": areas["optical_only"],
        "method_agreement_pct": agreement_pct,
        "optical_coverage_pct": coverage_pct,
        "confidence": round(min(0.95, 0.7 + (agreement_pct or 0) / 100 * 0.2), 2),
        "data_date": common.latest_image_date(current),
        "images_used": current_count,
        "method_note": (
            "Two independent methods (Sentinel-1 VV drop, Sentinel-2 NDWI) "
            "computed only where cloud-free optical exists. Teal = both agree; "
            "amber = radar only (could be wind-sheltered water or a radar "
            "artifact); blue = optical only (could be turbid shallow water "
            "radar misses, or an optical artifact)."
        ),
        "headline_stat": {
            "label": "Consensus flood extent",
            "value": areas["consensus"],
            "unit": "km²",
        },
    }
