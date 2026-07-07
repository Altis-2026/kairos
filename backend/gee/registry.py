from gee.flood import detect_flood
from gee.ships import detect_ships
from gee.fire import detect_burn_scar
from gee.oil import detect_oil_spill
from gee.deforestation import detect_deforestation
from gee.ice import detect_sea_ice
from gee.deformation import detect_deformation
from gee.flood_depth import estimate_flood_depth
from gee.damage import assess_damage
from gee.subsidence import detect_subsidence
from gee.urban import detect_urban_growth
from gee.agriculture import monitor_crops
from gee.mining import detect_land_disturbance

ANALYSIS_REGISTRY = {
    "flood_extent": {
        "function": detect_flood,
        "display_name": "Flood Extent Mapping",
        "description": (
            "Detects surface water inundation by measuring the drop in Sentinel-1 "
            "VV backscatter against a pre-flood baseline. Water returns almost no "
            "radar signal, so flooded land appears as anomalously dark patches."
        ),
        "category": "Disaster Response",
        "data_sources": ["S1"],
        "estimated_seconds": 20,
        "output_type": "raster",
        "color_palette": ["#00BFA8"],
        "icon": "waves",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "ship_detection": {
        "function": detect_ships,
        "display_name": "Ship Detection",
        "description": (
            "Detects vessels using CFAR-style adaptive thresholding. Ship hulls act "
            "as corner reflectors and appear as bright points against the dark ocean. "
            "Returns vessel positions and a total count."
        ),
        "category": "Maritime and Security",
        "data_sources": ["S1"],
        "estimated_seconds": 30,
        "output_type": "raster+points",
        "color_palette": ["#E8A318"],
        "icon": "ship",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "wildfire_burn_scar": {
        "function": detect_burn_scar,
        "display_name": "Wildfire Burn Scar Mapping",
        "description": (
            "Maps burn scars from the VH backscatter increase caused by fire removing "
            "vegetation and exposing bare rough soil. Works through smoke that makes "
            "optical satellites useless during active fires."
        ),
        "category": "Disaster Response",
        "data_sources": ["S1"],
        "estimated_seconds": 20,
        "output_type": "raster",
        "color_palette": ["#E8541E"],
        "icon": "flame",
        "sar_polarization": "VH",
        "instrument_mode": "IW",
    },
    "oil_spill": {
        "function": detect_oil_spill,
        "display_name": "Oil Spill Detection",
        "description": (
            "Oil films suppress the capillary waves that produce ocean radar "
            "backscatter, so slicks appear anomalously dark against clean water. "
            "Low-wind areas can produce false positives."
        ),
        "category": "Maritime and Security",
        "data_sources": ["S1"],
        "estimated_seconds": 25,
        "output_type": "raster",
        "color_palette": ["#7B61FF"],
        "icon": "droplets",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "deforestation": {
        "function": detect_deforestation,
        "display_name": "Deforestation and Forest Loss",
        "description": (
            "Detects forest clearing by comparing recent VH backscatter against a "
            "12-month historical baseline. Intact canopy is temporally stable; "
            "cleared land shows a fundamental backscatter shift."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 30,
        "output_type": "raster",
        "color_palette": ["#E84855"],
        "icon": "trees",
        "sar_polarization": "VH",
        "instrument_mode": "IW",
    },
    "sea_ice": {
        "function": detect_sea_ice,
        "display_name": "Sea Ice Extent",
        "description": (
            "Maps the boundary between open ocean and sea ice in polar regions "
            "using the strong backscatter contrast between ice and open water. "
            "Uses Sentinel-1 EW wide-swath polar acquisitions."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 25,
        "output_type": "raster",
        "color_palette": ["#BFEFFF"],
        "icon": "snowflake",
        "sar_polarization": "HH",
        "instrument_mode": "EW",
    },
    "surface_deformation": {
        "function": detect_deformation,
        "display_name": "Surface Deformation / Change",
        "description": (
            "Flags ground that has changed beyond its normal variability: "
            "subsidence, landslide scarring, construction or ground disturbance. "
            "Uses an amplitude temporal-coherence proxy: pixels whose recent VV "
            "backscatter deviates from a 12-month stability baseline by more than "
            "two standard deviations. (GRD amplitude, not phase InSAR.)"
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 35,
        "output_type": "raster",
        "color_palette": ["#C77DFF"],
        "icon": "activity",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "flood_depth": {
        "function": estimate_flood_depth,
        "display_name": "Flood Depth Estimation",
        "description": (
            "Goes beyond flood extent to estimate how deep the water is. Detects "
            "the flooded area from a >3 dB Sentinel-1 VV drop, then uses the "
            "Copernicus GLO-30 elevation model to estimate water depth from the "
            "shoreline elevation inward. Reports mean/max depth and water volume. "
            "(A simplified terrain approximation, not a hydraulic model.)"
        ),
        "category": "Disaster Response",
        "data_sources": ["S1", "DEM"],
        "estimated_seconds": 30,
        "output_type": "raster",
        "color_palette": ["#1E6FE8"],
        "icon": "waves",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "building_damage": {
        "function": assess_damage,
        "display_name": "Earthquake / Building Damage",
        "description": (
            "Maps likely-damaged buildings within hours of an earthquake, blast or "
            "strike, through the dust and cloud that blind optical satellites. "
            "Flags built-up pixels (JRC GHSL) whose Sentinel-1 VV signature changed "
            "sharply between a pre-event and post-event window, as collapse destroys "
            "a building's steady radar return. A rapid triage proxy for responders."
        ),
        "category": "Disaster Response",
        "data_sources": ["S1", "GHSL"],
        "estimated_seconds": 30,
        "output_type": "raster",
        "color_palette": ["#FF3B5C"],
        "icon": "building",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "land_subsidence": {
        "function": detect_subsidence,
        "display_name": "Land Subsidence Indicator",
        "description": (
            "Surfaces ground undergoing slow, progressive change: sinking cities, "
            "over-pumped aquifers, reworked land. Fits a straight-line trend to each "
            "pixel's VV backscatter over a long window and flags steep, consistent "
            "drifts. An amplitude-trend proxy that highlights candidate zones for a "
            "proper InSAR study, not millimetre InSAR displacement itself."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 40,
        "output_type": "raster",
        "color_palette": ["#1E6FE8"],
        "icon": "trending-down",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "urban_growth": {
        "function": detect_urban_growth,
        "display_name": "Urban Growth Monitoring",
        "description": (
            "Detects new construction and built-up expansion over the past year. "
            "Buildings and roads are bright radar corner reflectors, so new "
            "structures show a sharp, persistent rise in Sentinel-1 VV backscatter "
            "against a 12-month-prior baseline. Maps where the footprint of the "
            "built environment is growing."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 30,
        "output_type": "raster",
        "color_palette": ["#E8A318"],
        "icon": "building-2",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "crop_monitoring": {
        "function": monitor_crops,
        "display_name": "Agriculture / Crop Vigour",
        "description": (
            "Tracks crop health and cropland continuously, even through the cloud "
            "that blinds optical indices like NDVI for weeks. Computes the dual-pol "
            "Radar Vegetation Index (RVI) from Sentinel-1 VV+VH: a growing canopy "
            "scatters radar in all directions and raises VH, so the map reads "
            "directly as crop vigour from bare soil to dense canopy."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 25,
        "output_type": "raster",
        "color_palette": ["#7BC043"],
        "icon": "sprout",
        "sar_polarization": "VH",
        "instrument_mode": "IW",
    },
    "land_disturbance": {
        "function": detect_land_disturbance,
        "display_name": "Illegal Mining / Land Disturbance",
        "description": (
            "Surfaces candidate illegal mining and land clearing in remote, cloud-"
            "covered regions. Against a 12-month baseline it flags freshly cleared "
            "ground (a collapse in the VH canopy return) and new mirror-dark "
            "settling ponds (very low VV where there was no permanent water). Powers "
            "Kairos Guardian, where people help vet each detection. A lead for human "
            "review, not a verdict."
        ),
        "category": "Maritime and Security",
        "data_sources": ["S1"],
        "estimated_seconds": 35,
        "output_type": "raster",
        "color_palette": ["#FF6B2C"],
        "icon": "pickaxe",
        "sar_polarization": "VH",
        "instrument_mode": "IW",
    },
}


def registry_as_json() -> list:
    return [
        {
            "id": analysis_id,
            "display_name": cfg["display_name"],
            "description": cfg["description"],
            "category": cfg["category"],
            "data_sources": cfg["data_sources"],
            "estimated_seconds": cfg["estimated_seconds"],
            "output_type": cfg["output_type"],
            "color_palette": cfg["color_palette"],
            "icon": cfg["icon"],
        }
        for analysis_id, cfg in ANALYSIS_REGISTRY.items()
    ]
