"""
Sentinel-2 optical fusion — cross-sensor confirmation inside the detection
pipelines (not just a side-by-side overlay).

Radar backscatter is a proxy: rain-wet farmland can mimic flooding, harvests
can mimic burn scars. Where a cloud-free Sentinel-2 view exists inside the
analysis window, we test the SAR detection against the independent optical
signal (NDWI for water, dNBR for burns) and report the agreement, which the
caller folds into its confidence score. Clouds are expected — every function
here is called inside try/except and the SAR result stands alone when optical
is unavailable. That degradation is the whole reason Kairos leads with radar.

Data sources:
    COPERNICUS/S2_SR_HARMONIZED           surface reflectance
    GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED   per-pixel cloud score
"""

import ee
from gee import common

S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
CLOUD_SCORE_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"

# Cloud Score+ 'cs': 1 = definitely clear. 0.6 is the dataset's recommended
# default for masking.
_CS_CLEAR = 0.6
# NDWI (McFeeters, (G-NIR)/(G+NIR)) above zero reads as open water.
_NDWI_WATER = 0.0
# dNBR above ~0.27 is moderate-or-worse burn severity (Key & Benson, FIREMON).
_DNBR_BURN = 0.27
# NDVI drop of more than 0.2 between windows reads as vegetation loss.
_NDVI_LOSS = 0.2
# NDSI above 0.4 is the standard optical snow test (Dozier).
_NDSI_SNOW = 0.4


def _masked_composite(geometry: ee.Geometry, start_date: str, end_date: str) -> ee.Image:
    """Cloud-masked median Sentinel-2 composite; raises ValueError if no scenes."""
    s2 = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .linkCollection(ee.ImageCollection(CLOUD_SCORE_PLUS), ["cs"])
    )
    if s2.size().getInfo() == 0:
        raise ValueError("no Sentinel-2 scenes in window")
    masked = s2.map(lambda img: img.updateMask(img.select("cs").gte(_CS_CLEAR)))
    return masked.median()


def _agreement_stats(
    sar_mask: ee.Image,
    optical_mask: ee.Image,
    valid: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20,
) -> dict:
    """
    Fraction of the SAR detection confirmed by optical, computed only where a
    cloud-free optical view exists. One combined reduceRegion keeps this to a
    single round-trip.
    """
    sar = sar_mask.unmask(0).gt(0).rename("sar")
    opt = optical_mask.unmask(0).gt(0).rename("opt")
    both = sar.And(opt).rename("both")
    valid_px = valid.rename("valid")

    stack = (
        ee.Image.cat(
            [
                sar.updateMask(valid_px),
                both.updateMask(valid_px),
                valid_px,
            ]
        )
        .multiply(ee.Image.pixelArea())
    )
    sums = stack.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()

    aoi_m2 = geometry.area(maxError=100).getInfo()
    sar_m2 = float(sums.get("sar", 0) or 0)
    both_m2 = float(sums.get("both", 0) or 0)
    valid_m2 = float(sums.get("valid", 0) or 0)

    coverage_pct = round(100 * valid_m2 / aoi_m2, 1) if aoi_m2 else 0.0
    agreement_pct = round(100 * both_m2 / sar_m2, 1) if sar_m2 > 0 else None
    return {"coverage_pct": coverage_pct, "agreement_pct": agreement_pct}


def confidence_adjustment(agreement_pct, coverage_pct) -> float:
    """
    Modest, symmetric confidence nudge from optical agreement. Only meaningful
    when optical actually saw a decent share of the AOI; capped at ±0.08 so
    radar remains the primary evidence.
    """
    if agreement_pct is None or coverage_pct < 20:
        return 0.0
    return round(max(-0.08, min(0.08, 0.16 * (agreement_pct / 100 - 0.5))), 2)


def confirm_water(
    sar_mask: ee.Image, geometry: ee.Geometry, start_date: str, end_date: str
) -> dict:
    """
    Confirm a SAR water/flood mask against Sentinel-2 NDWI in the same window.
    Raises ValueError when no usable optical exists (caller catches).
    """
    composite = _masked_composite(geometry, start_date, end_date)
    ndwi = composite.normalizedDifference(["B3", "B8"])
    optical_water = ndwi.gt(_NDWI_WATER)
    valid = composite.select("B3").mask()

    stats = _agreement_stats(sar_mask, optical_water, valid, geometry)
    return {
        "optical_confirmation": "Sentinel-2 NDWI",
        "optical_coverage_pct": stats["coverage_pct"],
        "optical_agreement_pct": stats["agreement_pct"],
    }


def confirm_vegetation_loss(
    sar_mask: ee.Image,
    geometry: ee.Geometry,
    start_date: str,
    end_date: str,
    pre_start: str,
    pre_end: str,
) -> dict:
    """
    Confirm a SAR vegetation-loss mask (deforestation, land disturbance)
    against a Sentinel-2 NDVI drop between the pre and post windows.
    """
    post = _masked_composite(geometry, start_date, end_date)
    pre = _masked_composite(geometry, pre_start, pre_end)

    ndvi_post = post.normalizedDifference(["B8", "B4"])
    ndvi_pre = pre.normalizedDifference(["B8", "B4"])
    optical_loss = ndvi_pre.subtract(ndvi_post).gt(_NDVI_LOSS)
    valid = post.select("B8").mask().And(pre.select("B8").mask())

    stats = _agreement_stats(sar_mask, optical_loss, valid, geometry)
    return {
        "optical_confirmation": "Sentinel-2 NDVI change",
        "optical_coverage_pct": stats["coverage_pct"],
        "optical_agreement_pct": stats["agreement_pct"],
    }


def confirm_snow(
    sar_mask: ee.Image, geometry: ee.Geometry, start_date: str, end_date: str
) -> dict:
    """
    Confirm a SAR wet-snow mask against the Sentinel-2 NDSI snow test in the
    same window. Optical sees ALL snow (wet or dry) so agreement here means
    "the melt zone is at least snow-covered", not "the snow is wet".
    """
    composite = _masked_composite(geometry, start_date, end_date)
    ndsi = composite.normalizedDifference(["B3", "B11"])
    optical_snow = ndsi.gt(_NDSI_SNOW)
    valid = composite.select("B3").mask()

    stats = _agreement_stats(sar_mask, optical_snow, valid, geometry)
    return {
        "optical_confirmation": "Sentinel-2 NDSI",
        "optical_coverage_pct": stats["coverage_pct"],
        "optical_agreement_pct": stats["agreement_pct"],
    }


def confirm_burn(
    sar_mask: ee.Image,
    geometry: ee.Geometry,
    start_date: str,
    end_date: str,
    pre_start: str,
    pre_end: str,
) -> dict:
    """
    Confirm a SAR burn-scar mask against Sentinel-2 dNBR (pre-fire NBR minus
    post-fire NBR). Needs a usable composite in BOTH windows.
    """
    post = _masked_composite(geometry, start_date, end_date)
    pre = _masked_composite(geometry, pre_start, pre_end)

    nbr_post = post.normalizedDifference(["B8", "B12"])
    nbr_pre = pre.normalizedDifference(["B8", "B12"])
    dnbr = nbr_pre.subtract(nbr_post)
    optical_burn = dnbr.gt(_DNBR_BURN)
    valid = post.select("B8").mask().And(pre.select("B8").mask())

    stats = _agreement_stats(sar_mask, optical_burn, valid, geometry)
    return {
        "optical_confirmation": "Sentinel-2 dNBR",
        "optical_coverage_pct": stats["coverage_pct"],
        "optical_agreement_pct": stats["agreement_pct"],
    }
