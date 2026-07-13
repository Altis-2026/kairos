"""
The dataset scout's knowledge base: a curated index of Earth observation
datasets, every one of them free and already available on Google Earth Engine
(so anything Janus recommends, Kairos can actually touch).

Curated by hand rather than scraped: each entry carries what the catalog page
won't tell a beginner — what the data is genuinely good for and where it will
mislead you. The `limits` field is mandatory; a scout that only says nice
things is a salesperson.
"""

DATASETS = [
    {
        "id": "COPERNICUS/S1_GRD",
        "name": "Sentinel-1 SAR (GRD)",
        "measures": "C-band radar backscatter, VV/VH/HH, ~10 m",
        "cadence": "~12 days globally (6 where both satellites overlap)",
        "span": "2014-10 to present",
        "good_for": "floods, ships, deforestation, sea ice, surface change; all-weather, day/night",
        "limits": "amplitude only, no InSAR phase; speckle; wet soil and calm water mimic targets",
        "keywords": "radar sar sentinel-1 backscatter flood ship ice deforestation change all-weather",
    },
    {
        "id": "COPERNICUS/S2_SR_HARMONIZED",
        "name": "Sentinel-2 surface reflectance",
        "measures": "13-band optical, 10-20 m",
        "cadence": "~5 days",
        "span": "2017-03 to present (L2A)",
        "good_for": "NDVI/NDWI, land cover, burn severity (dNBR), visual confirmation of SAR detections",
        "limits": "blind under cloud and at night; that is often exactly when you need it",
        "keywords": "optical sentinel-2 ndvi ndwi dnbr true-color reflectance vegetation water burn",
    },
    {
        "id": "LANDSAT/LC09/C02/T1_L2",
        "name": "Landsat 8/9 surface reflectance",
        "measures": "11-band optical + thermal, 30 m",
        "cadence": "8 days combined",
        "span": "Landsat program back to 1982 (this collection 2021+)",
        "good_for": "long-horizon change studies, surface temperature, cross-checking Sentinel-2",
        "limits": "coarser than Sentinel-2; same cloud blindness",
        "keywords": "landsat optical thermal temperature long-term historical archive",
    },
    {
        "id": "MODIS/061/MCD64A1",
        "name": "MODIS burned area (MCD64A1)",
        "measures": "monthly burned-area day-of-burn, 500 m",
        "cadence": "monthly",
        "span": "2000-11 to present",
        "good_for": "ground truth for fire studies; regional/global burn statistics",
        "limits": "500 m misses small burns; ~1-2 month latency",
        "keywords": "fire burn scar ground-truth modis validation wildfire",
    },
    {
        "id": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1",
        "name": "Global Flood Database",
        "measures": "913 mapped historical flood events, 250 m",
        "cadence": "event-based",
        "span": "2000 to 2018",
        "good_for": "ground truth for flood detections; flood-frequency context",
        "limits": "ends 2018; 250 m; MODIS misses floods under cloud lasting < 2 days",
        "keywords": "flood ground-truth validation events historical dfo tellman",
    },
    {
        "id": "UMD/hansen/global_forest_change_2023_v1_11",
        "name": "Hansen Global Forest Change",
        "measures": "annual tree-cover loss year, 30 m",
        "cadence": "annual",
        "span": "2000 to 2023",
        "good_for": "ground truth for deforestation; where and when forest was lost",
        "limits": "annual only (no month); loss ≠ deforestation (fires and storms count too)",
        "keywords": "forest deforestation loss hansen ground-truth validation tree cover",
    },
    {
        "id": "JRC/GSW1_4/GlobalSurfaceWater",
        "name": "JRC Global Surface Water",
        "measures": "water occurrence/seasonality 1984-2021, 30 m",
        "cadence": "static summary",
        "span": "1984 to 2021",
        "good_for": "permanent-water masking, historical water dynamics, reservoir change",
        "limits": "optical heritage: polar and cloud gaps; ends 2021",
        "keywords": "water permanent occurrence river lake reservoir mask jrc",
    },
    {
        "id": "COPERNICUS/DEM/GLO30",
        "name": "Copernicus GLO-30 DEM",
        "measures": "elevation, 30 m",
        "cadence": "static",
        "span": "acquired 2011-2015",
        "good_for": "terrain context, flood-depth estimation, watershed logic",
        "limits": "a surface model (trees/buildings included); fixed in time",
        "keywords": "elevation dem terrain slope height watershed depth",
    },
    {
        "id": "ESA/WorldCover/v200",
        "name": "ESA WorldCover 2021",
        "measures": "11-class land cover, 10 m",
        "cadence": "static (2021)",
        "span": "2021",
        "good_for": "stratifying results by land cover; masking cropland vs forest vs urban",
        "limits": "single epoch; classes are broad",
        "keywords": "land cover classification cropland urban forest esa worldcover mask",
    },
    {
        "id": "JRC/GHSL/P2023A/GHS_POP",
        "name": "GHSL population grid",
        "measures": "people per ~100 m cell, 5-year epochs",
        "cadence": "5-year epochs",
        "span": "1975 to 2030 (modeled)",
        "good_for": "people-in-footprint impact figures for any detection",
        "limits": "modeled from census + built-up, not counted; epoch granularity",
        "keywords": "population people impact exposure ghsl census",
    },
    {
        "id": "JRC/GHSL/P2023A/GHS_BUILT_S",
        "name": "GHSL built-up surface",
        "measures": "built-up m² per cell",
        "cadence": "5-year epochs",
        "span": "1975 to 2030",
        "good_for": "urbanization studies; infrastructure exposure",
        "limits": "same modeling caveats as GHS_POP",
        "keywords": "built-up urban buildings infrastructure exposure ghsl",
    },
    {
        "id": "UCSB-CHG/CHIRPS/DAILY",
        "name": "CHIRPS daily precipitation",
        "measures": "rainfall estimate, ~5.5 km",
        "cadence": "daily",
        "span": "1981 to present",
        "good_for": "the confounder killer: did it rain before your 'flood'? drought context",
        "limits": "satellite+gauge blend; coarse; underestimates extremes in mountains",
        "keywords": "rain precipitation rainfall drought weather confounder chirps",
    },
    {
        "id": "ECMWF/ERA5_LAND/DAILY_AGGR",
        "name": "ERA5-Land daily",
        "measures": "temperature, wind, soil moisture, ~9 km",
        "cadence": "daily",
        "span": "1950 to present",
        "good_for": "wind speed for oil-slick false positives; soil moisture for flood confounders",
        "limits": "reanalysis (a model), 9 km; not point truth",
        "keywords": "wind temperature soil moisture weather reanalysis era5 confounder",
    },
    {
        "id": "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG",
        "name": "VIIRS nighttime lights",
        "measures": "monthly radiance of night lights, ~500 m",
        "cadence": "monthly",
        "span": "2012 to present",
        "good_for": "economic activity proxies, electrification, conflict blackouts, disaster recovery",
        "limits": "moonlight/aurora artifacts; radiance ≠ GDP",
        "keywords": "night lights economy electricity viirs blackout activity",
    },
    {
        "id": "MODIS/061/MOD13Q1",
        "name": "MODIS vegetation indices",
        "measures": "NDVI/EVI 16-day composites, 250 m",
        "cadence": "16 days",
        "span": "2000 to present",
        "good_for": "long vegetation time series, drought and phenology baselines",
        "limits": "250 m; composite artifacts in cloudy regions",
        "keywords": "ndvi evi vegetation phenology drought time-series modis",
    },
    {
        "id": "NASA/GPM_L3/IMERG_V07",
        "name": "GPM IMERG precipitation",
        "measures": "rainfall every 30 minutes, ~11 km",
        "cadence": "30 minutes",
        "span": "2000 to present",
        "good_for": "storm timing: exactly when the rain fell relative to a flood signal",
        "limits": "coarse; snow poorly handled",
        "keywords": "rain precipitation storm timing gpm imerg hourly",
    },
]


def search_datasets(query: str, limit: int = 5) -> list:
    """
    Rank the curated index against a free-text query. Deliberately simple
    keyword scoring — the index is small and hand-written, so recall matters
    more than clever ranking.
    """
    terms = [t for t in query.lower().split() if len(t) > 2]
    scored = []
    for ds in DATASETS:
        haystack = " ".join(
            [
                ds["name"].lower(),
                ds["measures"].lower(),
                ds["good_for"].lower(),
                ds["keywords"],
            ]
        )
        score = sum(haystack.count(t) for t in terms)
        if score > 0:
            scored.append((score, ds))
    scored.sort(key=lambda pair: -pair[0])
    results = [ds for _, ds in scored[:limit]]
    # An empty result should still teach: return the two core sensors.
    if not results:
        results = DATASETS[:2]
    return [{k: v for k, v in ds.items() if k != "keywords"} for ds in results]
