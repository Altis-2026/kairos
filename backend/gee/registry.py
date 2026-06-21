"""
The AnalysisRegistry: the single source of truth for every Kairos analysis type.

To add a new analysis type:
  1. Write the GEE function in a new file (e.g. gee/wetland.py)
  2. Import it here
  3. Add ONE entry to this dict
Nothing else in the codebase changes. The /registry endpoint serializes this
dict, and the frontend sidebar builds itself from that response.
"""

from gee.flood import detect_flood
from gee.ships import detect_ships
from gee.fire import detect_burn_scar
from gee.oil import detect_oil_spill
from gee.deforestation import detect_deforestation
from gee.ice import detect_sea_ice
from gee.deformation import detect_deformation

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
            "Flags ground that has changed beyond its normal variability — "
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
}


def registry_as_json() -> list:
    """Serializable registry for the GET /registry endpoint (drops the callables)."""
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
