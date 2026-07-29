import ee
from datetime import datetime, timedelta

from gee import common

CHIRPS = "UCSB-CHG/CHIRPS/DAILY"
ERA5_LAND = "ECMWF/ERA5_LAND/DAILY_AGGR"
WORLDCOVER = "ESA/WorldCover/v200"

LC_CROPLAND = 40
LC_BUILTUP = 50

LEAD_DAYS = 5


def _mean_over(image: ee.Image, geometry: ee.Geometry, band: str, scale: int):
    return image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
    ).get(band)


def _rainfall(geometry, start_date, end_date) -> dict:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    lead_start = (start - timedelta(days=LEAD_DAYS)).strftime("%Y-%m-%d")

    def total_mm(a, b):
        coll = ee.ImageCollection(CHIRPS).filterDate(a, b).select("precipitation")
        if coll.size().getInfo() == 0:
            return None
        img = coll.sum()
        v = _mean_over(img, geometry, "precipitation", 5500).getInfo()
        return round(float(v), 1) if v is not None else None

    return {
        "window_mm": total_mm(start_date, end_date),
        "lead_5day_mm": total_mm(lead_start, start_date),
    }


def _wind(geometry, start_date, end_date) -> dict:
    coll = ee.ImageCollection(ERA5_LAND).filterDate(start_date, end_date)
    if coll.size().getInfo() == 0:
        return {"mean_ms": None}
    img = coll.mean()
    speed = (
        img.select("u_component_of_wind_10m")
        .pow(2)
        .add(img.select("v_component_of_wind_10m").pow(2))
        .sqrt()
        .rename("wind")
    )
    v = _mean_over(speed, geometry, "wind", 9000).getInfo()
    return {"mean_ms": round(float(v), 1) if v is not None else None}


def _land_cover(geometry) -> dict:
    # WorldCover is tiled, so mosaic it; .first() would return one tile that
    # usually misses the AOI.
    lc = ee.ImageCollection(WORLDCOVER).mosaic().select("Map")
    area = ee.Image.pixelArea()
    stacked = ee.Image.cat(
        [
            area.updateMask(lc.eq(LC_CROPLAND)).rename("cropland"),
            area.updateMask(lc.eq(LC_BUILTUP)).rename("built_up"),
            area.rename("total"),
        ]
    )
    stats = stacked.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=100,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    whole = float(stats.get("total") or 0)
    fractions = {}
    for name in ("cropland", "built_up"):
        part = float(stats.get(name) or 0)
        fractions[name] = round(100 * part / whole, 1) if whole else 0.0
    return fractions


def _interpret(analysis_type, rain, wind, lc) -> list:
    findings = []
    lead = rain.get("lead_5day_mm")
    win = rain.get("window_mm")
    cropland = lc.get("cropland")
    built = lc.get("built_up")
    wind_ms = wind.get("mean_ms")

    def add(variable, finding, concern):
        findings.append(
            {"variable": variable, "finding": finding, "concern": concern}
        )

    if analysis_type in ("flood_extent", "flood_depth"):
        if lead is not None:
            if lead >= 30:
                add(
                    "rainfall",
                    f"{lead} mm of rain fell in the 5 days before your window. "
                    "Heavy antecedent rain wets soil and can darken backscatter "
                    "like standing water does.",
                    "high",
                )
            elif lead >= 8:
                add(
                    "rainfall",
                    f"{lead} mm fell in the 5 days before the window, which is "
                    "moderate; soil wetting is a partial alternative "
                    "explanation.",
                    "some",
                )
            else:
                add(
                    "rainfall",
                    f"Only {lead} mm fell before the window, so rain-wetted "
                    "soil is an unlikely explanation for a dark signal.",
                    "low",
                )
        if cropland is not None and cropland >= 25:
            add(
                "land_cover",
                f"{cropland}% of the area is cropland. Ploughed or irrigated "
                "fields can mimic flooding in radar; mask cropland before "
                "trusting the extent.",
                "some",
            )

    elif analysis_type == "oil_spill":
        if wind_ms is not None:
            if wind_ms < 3:
                add(
                    "wind",
                    f"Mean wind was {wind_ms} m/s. Below about 3 m/s the sea "
                    "surface flattens and reads dark without oil, the classic "
                    "oil-slick false positive.",
                    "high",
                )
            elif wind_ms > 10:
                add(
                    "wind",
                    f"Mean wind was {wind_ms} m/s. High wind roughens the sea "
                    "and can hide a real slick, so absence of signal is not "
                    "absence of oil.",
                    "some",
                )
            else:
                add(
                    "wind",
                    f"Mean wind was {wind_ms} m/s, in the band where oil "
                    "suppresses backscatter cleanly. Good conditions for this "
                    "detection.",
                    "low",
                )

    elif analysis_type in ("deforestation", "land_disturbance"):
        if cropland is not None and cropland >= 25:
            add(
                "land_cover",
                f"{cropland}% of the area is cropland. Harvest and ploughing "
                "drop VH backscatter just like clearing does; confirm the "
                "change is forest, not a farmed field's season.",
                "high",
            )
        if lead is not None and lead >= 30:
            add(
                "rainfall",
                f"{lead} mm of rain before the window can change canopy "
                "backscatter independently of any clearing.",
                "some",
            )

    elif analysis_type == "wildfire_burn_scar":
        if win is not None and win >= 30:
            add(
                "rainfall",
                f"{win} mm of rain fell during the window. Rain changes soil "
                "roughness and moisture and can muddy a burn-scar signal.",
                "some",
            )
        if cropland is not None and cropland >= 30:
            add(
                "land_cover",
                f"{cropland}% cropland: agricultural burning and harvest can "
                "resemble wildfire scars.",
                "some",
            )

    elif analysis_type in ("urban_growth", "building_damage"):
        if built is not None:
            add(
                "land_cover",
                f"{built}% of the area is already built-up, the relevant base "
                "rate for reading a change in the built environment.",
                "low",
            )

    if not findings:
        findings.append(
            {
                "variable": "none",
                "finding": "No standard environmental confounder for this "
                "analysis type showed a strong signal in the pulled data.",
                "concern": "low",
            }
        )
    return findings


def analyze_confounders(
    analysis_type: str, bbox: list, start_date: str, end_date: str
) -> dict:
    geometry = common.bbox_geometry(bbox)
    rain = _rainfall(geometry, start_date, end_date)
    wind = _wind(geometry, start_date, end_date)
    lc = _land_cover(geometry)

    findings = _interpret(analysis_type, rain, wind, lc)
    concerns = [f["concern"] for f in findings]
    overall = (
        "high" if "high" in concerns else "some" if "some" in concerns else "low"
    )

    return {
        "analysis_type": analysis_type,
        "measurements": {"rainfall": rain, "wind": wind, "land_cover": lc},
        "findings": findings,
        "overall_concern": overall,
    }
