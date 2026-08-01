"""
Foresight — hazard exposure outlooks from the measured satellite record.

This is deliberately NOT a forecast. Each function answers three questions for
one place, using decades of public observations and nothing else:

  1. How exposed is this area to the hazard, historically? (0-100 score)
  2. When in the year does it peak?
  3. Is it getting worse? (OLS + Mann-Kendall, only reported when significant)

Every number is computed live from a public archive when the request comes in,
so anyone can check it against the same data. Where a claim cannot be backed by
the record — a trend with too few years, a skill score with no independent
reference — the function returns None rather than guessing.

The scoring constants (e.g. burned fraction x 300) are transparent linear
scalings chosen so that typical exposed areas land in a readable 0-100 band.
They are stated in each `method` string rather than hidden, because they are
conventions, not physics.
"""

import ee
from datetime import date, timedelta

import stats
from gee import common

GSW = "JRC/GSW1_4/GlobalSurfaceWater"
GSW_MONTHLY = "JRC/GSW1_4/MonthlyRecurrence"
GSW_YEARLY = "JRC/GSW1_4/YearlyHistory"
GLOBAL_FLOOD_DB = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
MCD64A1 = "MODIS/061/MCD64A1"
CHIRPS_PENTAD = "UCSB-CHG/CHIRPS/PENTAD"
WORLDCOVER = "ESA/WorldCover/v200"

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

FLOOD_PALETTE = ["#00BFA8", "#7BC043", "#E8A318", "#FF3B5C"]
FIRE_PALETTE = ["#E8A318", "#FF7A3B", "#FF3B5C", "#B3123B"]
DROUGHT_PALETTE = ["#FF3B5C", "#E8A318", "#E8EFE9", "#3BA7FF", "#1E6FE8"]


def _level(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "moderate"
    if score < 75:
        return "high"
    return "very high"


def _area_fraction(mask: ee.Image, geometry: ee.Geometry, scale: int) -> float:
    """Fraction of the AOI where `mask` is set, by true pixel area."""
    stacked = ee.Image.cat(
        [
            ee.Image.pixelArea().updateMask(mask).rename("part"),
            ee.Image.pixelArea().rename("total"),
        ]
    )
    sums = stacked.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    total = float(sums.get("total") or 0)
    part = float(sums.get("part") or 0)
    return part / total if total > 0 else 0.0


def _monthly_profile(values: list) -> dict:
    """Twelve monthly values plus the months within 60% of the peak."""
    total = sum(values)
    if total <= 0:
        return {"months": values, "peak_months": []}
    peak = max(values)
    peak_months = [
        MONTH_NAMES[i] for i, v in enumerate(values) if v >= 0.6 * peak and v > 0
    ]
    return {"months": [round(v, 3) for v in values], "peak_months": peak_months}


def _yearly_series(fc_info: dict, key: str) -> list:
    points = []
    for feat in fc_info.get("features", []):
        props = feat.get("properties", {})
        year = props.get("year")
        value = props.get(key)
        if year is not None and value is not None:
            points.append({"date": f"{int(year)}-07-01", "value": float(value)})
    points.sort(key=lambda p: p["date"])
    return points


def _safe_trend(points: list):
    """A trend test, or None when the record cannot support one."""
    if len(points) < 4:
        return None
    values = [p["value"] for p in points]
    if len(set(values)) < 2:
        return None
    try:
        return stats.trend_report(points)
    except ValueError:
        return None


def flood_risk(bbox: list) -> dict:
    geometry = common.bbox_geometry(bbox)
    gsw = ee.Image(GSW)
    occurrence = gsw.select("occurrence").unmask(0)

    # 5-85% of observations wet = flood-prone; above that it is a water body.
    prone = occurrence.gte(5).And(occurrence.lt(85))
    permanent = occurrence.gte(85)

    prone_frac = _area_fraction(prone, geometry, 60)
    permanent_frac = _area_fraction(permanent, geometry, 60)

    # Score against the land area, so a coastal AOI is not diluted by ocean.
    land_frac = 1.0 - permanent_frac
    exposure = prone_frac / land_frac if land_frac > 0.02 else prone_frac
    score = round(min(100.0, exposure * 400))

    styled = occurrence.updateMask(prone).clip(geometry)
    tile = common.tile_url(styled, {"min": 5, "max": 85, "palette": FLOOD_PALETTE})

    monthly = ee.ImageCollection(GSW_MONTHLY).select("monthly_recurrence")

    def month_mean(img):
        v = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=200,
            maxPixels=1e10,
            bestEffort=True,
        ).get("monthly_recurrence")
        return ee.Feature(None, {"month": img.get("month"), "value": v})

    month_info = monthly.map(month_mean).getInfo()
    month_vals = [0.0] * 12
    for feat in month_info.get("features", []):
        props = feat.get("properties", {})
        m = props.get("month")
        v = props.get("value")
        if m is not None and v is not None:
            month_vals[int(m) - 1] = float(v)
    seasonal = _monthly_profile(month_vals)

    yearly = ee.ImageCollection(GSW_YEARLY).filter(
        ee.Filter.rangeContains("year", 2010, 2021)
    )

    def year_area(img):
        seasonal_water = img.select("waterClass").eq(2)
        area = (
            ee.Image.pixelArea()
            .updateMask(seasonal_water)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=120,
                maxPixels=1e10,
                bestEffort=True,
            )
            .get("area")
        )
        return ee.Feature(
            None, {"year": img.get("year"), "km2": ee.Number(area).divide(1e6)}
        )

    trend_points = _yearly_series(yearly.map(year_area).getInfo(), "km2")
    trend = _safe_trend(trend_points)

    # Self-graded skill: how much independently mapped flooding lands inside
    # the zones this method calls flood-prone. Computed, never asserted.
    skill = None
    try:
        events = ee.ImageCollection(GLOBAL_FLOOD_DB).filterBounds(geometry)
        if events.size().getInfo() > 0:
            observed = events.select("flooded").max().gt(0).unmask(0)
            observed = observed.where(permanent, 0)
            hit = observed.And(prone)
            sums = (
                ee.Image.cat(
                    [
                        ee.Image.pixelArea().updateMask(observed).rename("obs"),
                        ee.Image.pixelArea().updateMask(hit).rename("hit"),
                    ]
                )
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=geometry,
                    scale=250,
                    maxPixels=1e10,
                    bestEffort=True,
                )
                .getInfo()
            )
            obs = float(sums.get("obs") or 0)
            hits = float(sums.get("hit") or 0)
            if obs > 0:
                skill = {
                    "hit_rate": round(hits / obs, 3),
                    "reference": "Global Flood Database (Tellman et al. 2021)",
                    "note": (
                        "Fraction of independently mapped flood extent in this "
                        "area that falls inside the zones Kairos marks as "
                        "flood-prone. Computed live against MODIS-mapped "
                        "events, not asserted."
                    ),
                }
    except Exception:
        skill = None

    drivers = [
        f"{round(prone_frac * 100, 1)}% of this area has been under water at "
        "least occasionally in the 38-year Landsat water record (1984-2021) "
        "without being a permanent water body.",
        f"Permanent water covers {round(permanent_frac * 100, 1)}% of the area.",
    ]

    return {
        "hazard": "flood",
        "score": score,
        "level": _level(score),
        "tile_url": tile,
        "legend_label": "Historical flood frequency (% of observations wet)",
        "drivers": drivers,
        "seasonal": seasonal,
        "seasonal_label": "Water recurrence by month (JRC monthly record)",
        "trend": trend,
        "trend_label": "Seasonal water area per year, 2010-2021 (km2)",
        "trend_points": trend_points,
        "skill": skill,
        "method": (
            "Flood proneness comes from the JRC Global Surface Water record: "
            "every Landsat observation since 1984, per 30 m pixel. Pixels wet "
            "in 5-85% of observations are flood-prone; above 85% is permanent "
            "water. This is measured history, not a simulation."
        ),
        "data_years": "1984-2021",
    }


def wildfire_risk(bbox: list) -> dict:
    geometry = common.bbox_geometry(bbox)
    burns = ee.ImageCollection(MCD64A1).select("BurnDate").filterDate(
        "2001-01-01", f"{date.today().year}-01-01"
    )

    burn_count = burns.map(lambda img: img.gt(0).unmask(0)).sum().rename("count")
    burned_ever = burn_count.gt(0)
    burned_frac = _area_fraction(burned_ever, geometry, 500)

    # WorldCover 10/20/30 = trees / shrubland / grassland: the fuel that carries fire.
    lc = ee.ImageCollection(WORLDCOVER).mosaic().select("Map")
    fuel = lc.eq(10).Or(lc.eq(20)).Or(lc.eq(30))
    fuel_frac = _area_fraction(fuel, geometry, 100)

    score = round(min(100.0, burned_frac * 300 + fuel_frac * 40))

    styled = burn_count.updateMask(burned_ever).clip(geometry)
    tile = common.tile_url(styled, {"min": 1, "max": 6, "palette": FIRE_PALETTE})

    def month_area(m):
        m = ee.Number(m)
        monthly = burns.filter(ee.Filter.calendarRange(m, m, "month"))
        img = monthly.map(lambda i: i.gt(0).unmask(0)).sum().gt(0)
        area = (
            ee.Image.pixelArea()
            .updateMask(img)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=500,
                maxPixels=1e10,
                bestEffort=True,
            )
            .get("area")
        )
        return ee.Feature(None, {"month": m, "km2": ee.Number(area).divide(1e6)})

    month_fc = ee.FeatureCollection(ee.List.sequence(1, 12).map(month_area)).getInfo()
    month_vals = [0.0] * 12
    for feat in month_fc.get("features", []):
        props = feat.get("properties", {})
        m = props.get("month")
        v = props.get("km2")
        if m is not None and v is not None:
            month_vals[int(m) - 1] = float(v)
    seasonal = _monthly_profile(month_vals)

    def year_area(y):
        y = ee.Number(y)
        yearly = burns.filter(ee.Filter.calendarRange(y, y, "year"))
        img = yearly.map(lambda i: i.gt(0).unmask(0)).sum().gt(0)
        area = (
            ee.Image.pixelArea()
            .updateMask(img)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=500,
                maxPixels=1e10,
                bestEffort=True,
            )
            .get("area")
        )
        return ee.Feature(None, {"year": y, "km2": ee.Number(area).divide(1e6)})

    last_full_year = date.today().year - 1
    years = ee.List.sequence(2001, last_full_year)
    trend_points = _yearly_series(
        ee.FeatureCollection(years.map(year_area)).getInfo(), "km2"
    )
    trend = _safe_trend(trend_points)

    drivers = [
        f"{round(burned_frac * 100, 1)}% of this area has burned at least once "
        "since 2001 in the MODIS burned-area record.",
        f"{round(fuel_frac * 100, 1)}% is vegetation that can carry fire "
        "(trees, shrub or grassland in ESA WorldCover).",
    ]

    return {
        "hazard": "wildfire",
        "score": score,
        "level": _level(score),
        "tile_url": tile,
        "legend_label": "Times burned since 2001 (MODIS)",
        "drivers": drivers,
        "seasonal": seasonal,
        "seasonal_label": "Burned area by calendar month since 2001 (km2)",
        "trend": trend,
        "trend_label": f"Burned area per year, 2001-{last_full_year} (km2)",
        "trend_points": trend_points,
        "skill": None,
        "method": (
            "Fire proneness combines two measured records: how often each "
            "500 m pixel has burned since 2001 (MODIS MCD64A1) and how much "
            "of the area is burnable vegetation (ESA WorldCover). The score "
            "is burned fraction x 300 plus fuel fraction x 40, capped at 100."
        ),
        "data_years": f"2001-{last_full_year}",
    }


def drought_risk(bbox: list) -> dict:
    geometry = common.bbox_geometry(bbox)
    chirps = ee.ImageCollection(CHIRPS_PENTAD).select("precipitation")

    today = date.today()
    recent_start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    recent = chirps.filterDate(recent_start, today.strftime("%Y-%m-%d")).sum()

    baseline_years = list(range(today.year - 11, today.year - 1))

    def year_total(y):
        y = ee.Number(y)
        img = chirps.filter(ee.Filter.calendarRange(y, y, "year")).sum()
        total = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=5500,
            maxPixels=1e10,
            bestEffort=True,
        ).get("precipitation")
        return ee.Feature(None, {"year": y, "mm": total})

    yearly_fc = ee.FeatureCollection(
        ee.List.sequence(baseline_years[0], baseline_years[-1]).map(year_total)
    ).getInfo()
    trend_points = _yearly_series(yearly_fc, "mm")

    baseline_vals = [p["value"] for p in trend_points]
    baseline_mean = sum(baseline_vals) / len(baseline_vals) if baseline_vals else None

    recent_mm_raw = recent.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=5500,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo().get("precipitation")
    recent_mm = round(float(recent_mm_raw), 1) if recent_mm_raw is not None else None

    deficit_pct = None
    if baseline_mean and recent_mm is not None and baseline_mean > 0:
        deficit_pct = round(100 * (baseline_mean - recent_mm) / baseline_mean, 1)

    score = 0
    if deficit_pct is not None:
        score = round(max(0.0, min(100.0, deficit_pct * 2.5)))

    trend = _safe_trend(trend_points)
    if trend and trend["mann_kendall"]["trend"] == "decreasing":
        score = min(100, score + 15)

    baseline_img = (
        chirps.filter(
            ee.Filter.calendarRange(baseline_years[0], baseline_years[-1], "year")
        )
        .sum()
        .divide(len(baseline_years))
    )
    anomaly = (
        recent.subtract(baseline_img)
        .divide(baseline_img.max(ee.Image.constant(1)))
        .clip(geometry)
    )
    tile = common.tile_url(anomaly, {"min": -0.6, "max": 0.6, "palette": DROUGHT_PALETTE})

    def month_mean(m):
        m = ee.Number(m)
        img = chirps.filter(ee.Filter.calendarRange(m, m, "month")).mean()
        v = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=5500,
            maxPixels=1e10,
            bestEffort=True,
        ).get("precipitation")
        return ee.Feature(None, {"month": m, "mm": v})

    month_fc = ee.FeatureCollection(ee.List.sequence(1, 12).map(month_mean)).getInfo()
    month_vals = [0.0] * 12
    for feat in month_fc.get("features", []):
        props = feat.get("properties", {})
        m = props.get("month")
        v = props.get("mm")
        if m is not None and v is not None:
            month_vals[int(m) - 1] = float(v)
    seasonal = _monthly_profile(month_vals)

    drivers = []
    if recent_mm is not None and baseline_mean:
        drivers.append(
            f"The last 12 months brought {recent_mm} mm of rain against a "
            f"{round(baseline_mean, 1)} mm ten-year average."
        )
    if deficit_pct is not None:
        if deficit_pct > 0:
            drivers.append(
                f"That is a {deficit_pct}% rainfall deficit versus the "
                "long-term normal."
            )
        else:
            drivers.append(
                f"Rainfall is {abs(deficit_pct)}% above the long-term normal."
            )

    return {
        "hazard": "drought",
        "score": score,
        "level": _level(score),
        "tile_url": tile,
        "legend_label": "12-month rainfall anomaly (red dry, blue wet)",
        "drivers": drivers,
        "seasonal": seasonal,
        "seasonal_label": "Average rainfall by month (CHIRPS pentads, mm)",
        "trend": trend,
        "trend_label": "Annual rainfall over the last decade (mm)",
        "trend_points": trend_points,
        "skill": None,
        "method": (
            "Drought stress compares the last 12 months of CHIRPS satellite "
            "rainfall against the ten-year normal for the same area. The "
            "score is 2.5 points per percent deficit, plus 15 if the decade "
            "trend is significantly drying (Mann-Kendall p under 0.05)."
        ),
        "data_years": f"{baseline_years[0]}-{today.year}",
    }


def subsidence_risk(bbox: list) -> dict:
    from gee.subsidence import detect_subsidence

    today = date.today()
    end = today.strftime("%Y-%m-%d")
    start = (today - timedelta(days=365)).strftime("%Y-%m-%d")

    raw = detect_subsidence(bbox, start, end)

    geometry = common.bbox_geometry(bbox)
    flagged_frac = _area_fraction(raw["result_image"], geometry, 60)
    score = round(min(100.0, flagged_frac * 600))

    drivers = [
        f"{raw['trend_area_km2']} km2 shows a progressive radar amplitude "
        f"trend across {raw['images_used']} Sentinel-1 passes in the last "
        "12 months.",
        "Amplitude trends flag candidate ground change; confirming true "
        "vertical motion needs phase InSAR like the products in the InSAR "
        "panel.",
    ]

    return {
        "hazard": "subsidence",
        "score": score,
        "level": _level(score),
        "tile_url": raw["tile_url"],
        "legend_label": "Radar amplitude trend (blue falling, red rising)",
        "drivers": drivers,
        "seasonal": {"months": [], "peak_months": []},
        "seasonal_label": None,
        "trend": None,
        "trend_label": None,
        "trend_points": [],
        "skill": None,
        "method": (
            "Runs the production ground-change detector over the last 12 "
            "months: a per-pixel linear fit of Sentinel-1 VV amplitude "
            "against time, screened for persistent-scatterer stability and "
            "temporal consistency. This is an amplitude proxy and flags "
            "candidates; it does not measure millimetre motion the way phase "
            "InSAR does, and the method label says so."
        ),
        "data_years": f"{start} to {end}",
    }


RISK_FUNCTIONS = {
    "flood": flood_risk,
    "wildfire": wildfire_risk,
    "drought": drought_risk,
    "subsidence": subsidence_risk,
}
