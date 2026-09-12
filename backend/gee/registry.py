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
from gee.ice_drift import track_ice_drift
from gee.deformation import detect_deformation
from gee.flood_depth import estimate_flood_depth
from gee.damage import assess_damage
from gee.subsidence import detect_subsidence
from gee.urban import detect_urban_growth
from gee.agriculture import monitor_crops
from gee.mining import detect_land_disturbance
from gee.biomass import estimate_biomass
from gee.atmosphere import detect_methane, monitor_air_quality
from gee.soil_moisture import estimate_soil_moisture
from gee.flooded_forest import detect_flooded_forest
from gee.snow import detect_wet_snow
from gee.consensus import flood_consensus
from gee.archaeology import detect_anomalies
from solver.fire_behavior import FUEL_MODELS
from solver.fire_presets import SCENES as FIRE_SCENES
from solver.fire_sim import simulate_fire
from solver.flood_sim import simulate_flood
from solver.presets import SCENE_IDS

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
    "ice_drift": {
        "function": track_ice_drift,
        "display_name": "Sea Ice Drift Tracking",
        "description": (
            "Measures how fast and in which direction the ice is moving, by "
            "cross-correlating radar texture between two passes to track the "
            "same floes through time. Sea ice extent says where the ice is; "
            "drift says where it is going."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 35,
        "output_type": "raster",
        "color_palette": ["#0B3B5C", "#1E6FE8", "#00BFA8", "#BFEFFF", "#FFFFFF"],
        "icon": "wind",
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
            "strike — through the dust and cloud that blind optical satellites. "
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
            "Surfaces ground undergoing slow, progressive change — sinking cities, "
            "over-pumped aquifers, reworked land. Fits a straight-line trend to each "
            "pixel's VV backscatter, then screens it with the two tests real PSInSAR "
            "uses to pick measurement points: amplitude-dispersion stability "
            "(persistent scatterers) and temporal consistency. Highlights candidate "
            "zones for a proper InSAR study, not millimetre displacement itself."
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
            "Tracks crop health and cropland continuously — even through the cloud "
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
    "forest_biomass": {
        "function": estimate_biomass,
        "display_name": "Forest Biomass & Structure",
        "description": (
            "Estimates above-ground forest biomass by fusing two satellites. "
            "ALOS PALSAR L-band radar penetrates the canopy and scatters off "
            "trunks and branches (its HV return rises with woody biomass), and "
            "Sentinel-2 optical NDVI confirms the pixels are genuinely live "
            "vegetation. A rough saturating proxy in Mg/ha, not a calibrated "
            "inventory: L-band saturates over the densest tropical forest."
        ),
        "category": "Environmental",
        "data_sources": ["PALSAR", "S2"],
        "estimated_seconds": 35,
        "output_type": "raster",
        "color_palette": ["#2E8B3D"],
        "icon": "trees",
        "sar_polarization": "HV",
        "instrument_mode": "PALSAR",
    },
    "methane": {
        "function": detect_methane,
        "display_name": "Methane Monitoring",
        "description": (
            "Maps the methane column from Sentinel-5P (TROPOMI) and flags "
            "enhancement zones well above the local background — candidate "
            "emission areas like oil and gas fields, landfills and wetlands. "
            "Coarse (~7 km) and column-integrated, so it finds regional "
            "enhancements, not a single smokestack."
        ),
        "category": "Environmental",
        "data_sources": ["S5P"],
        "estimated_seconds": 20,
        "output_type": "raster",
        "color_palette": ["#00BFA8"],
        "icon": "wind",
        "sar_polarization": None,
        "instrument_mode": "TROPOMI",
    },
    "air_quality": {
        "function": monitor_air_quality,
        "display_name": "Air Quality (NO2)",
        "description": (
            "Maps tropospheric nitrogen dioxide from Sentinel-5P (TROPOMI), a "
            "marker of combustion from traffic, power plants and industry, and "
            "flags pollution hotspots above the local mean. Column-integrated "
            "and ~7 km, so it reads city- and region-scale pollution patterns."
        ),
        "category": "Environmental",
        "data_sources": ["S5P"],
        "estimated_seconds": 20,
        "output_type": "raster",
        "color_palette": ["#E8A318"],
        "icon": "factory",
        "sar_polarization": None,
        "instrument_mode": "TROPOMI",
    },
    "soil_moisture": {
        "function": estimate_soil_moisture,
        "display_name": "Surface Soil Moisture",
        "description": (
            "Relative surface soil moisture from Sentinel-1 change detection: "
            "each pixel's VV backscatter is placed between its own 12-month "
            "dry and wet extremes (0 = driest observed, 1 = wettest). Masked "
            "where dense forest, cities, water or snow break the physics. A "
            "relative index of the top ~5 cm, not volumetric ground truth."
        ),
        "category": "Agriculture",
        "data_sources": ["S1"],
        "estimated_seconds": 25,
        "output_type": "raster",
        "color_palette": ["#8B5A2B", "#00BFA8"],
        "icon": "droplets",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "flooded_forest": {
        "function": detect_flooded_forest,
        "display_name": "Flooded Forest / Mangrove",
        "description": (
            "Finds water standing UNDER tree canopy — invisible to optical "
            "satellites — via the double-bounce brightening (VV rise > +3 dB) "
            "that flooded trunks produce. Runs only inside WorldCover tree and "
            "mangrove pixels. The complement of open-water flood mapping."
        ),
        "category": "Disaster Response",
        "data_sources": ["S1"],
        "estimated_seconds": 25,
        "output_type": "raster",
        "color_palette": ["#00BFA8"],
        "icon": "trees",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "wet_snow": {
        "function": detect_wet_snow,
        "display_name": "Wet Snow / Melt Extent",
        "description": (
            "Maps melting snow with the Nagler ratio method: liquid water in "
            "the snowpack absorbs C-band radar, so wet snow sits >3 dB below a "
            "frozen mid-winter reference. Reports melt extent and its elevation "
            "band. Extent only — C-band cannot measure depth or snow water "
            "equivalent."
        ),
        "category": "Environmental",
        "data_sources": ["S1"],
        "estimated_seconds": 25,
        "output_type": "raster",
        "color_palette": ["#7FD8FF"],
        "icon": "snowflake",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "flood_consensus": {
        "function": flood_consensus,
        "display_name": "Flood Consensus (SAR + Optical)",
        "description": (
            "Runs two independent flood methods — Sentinel-1 backscatter drop "
            "and Sentinel-2 NDWI — and maps where they agree (teal), where only "
            "radar sees water (amber) and where only optical does (blue). "
            "Needs a usable cloud-free optical share; refuses to fake a "
            "consensus when clouds block it."
        ),
        "category": "Disaster Response",
        "data_sources": ["S1", "S2"],
        "estimated_seconds": 40,
        "output_type": "raster",
        "color_palette": ["#E8A318", "#3BA7FF", "#00BFA8"],
        "icon": "layers",
        "sar_polarization": "VV",
        "instrument_mode": "IW",
    },
    "flood_simulation": {
        "function": simulate_flood,
        "display_name": "Flood Simulation (forward model)",
        "description": (
            "SIMULATED, not observed. Routes an assumed inflow hydrograph over "
            "real Copernicus GLO-30 terrain with a local-inertial shallow-water "
            "solver, producing an animated rise and recession instead of a "
            "single snapshot. Answers 'where would water go?' — the question "
            "radar cannot answer, because the flood has not happened. For a "
            "flood that did happen, use Flood Extent Mapping."
        ),
        "category": "Simulation (forward model)",
        "data_sources": ["GLO-30"],
        "estimated_seconds": 120,
        "output_type": "simulation",
        "color_palette": ["#3BA7FF", "#7B61FF", "#E85CCF"],
        "icon": "waves",
        "mode": "simulated",
        "accepts_params": True,
        "params_schema": {
            "scene": {
                "type": "string",
                "label": "Showcase scene",
                "help": "Preset AOI and hydrograph. Overrides the AOI box.",
                "enum": list(SCENE_IDS),
                "default": None,
            },
            "peak_discharge_m3s": {
                "type": "number", "label": "Peak inflow", "unit": "m3/s",
                "default": 300.0, "min": 1.0, "max": 20000.0,
            },
            "rise_minutes": {
                "type": "number", "label": "Rise to peak", "unit": "min",
                "default": 30.0, "min": 0.0, "max": 1440.0,
            },
            "peak_minutes": {
                "type": "number", "label": "Time at peak", "unit": "min",
                "default": 30.0, "min": 0.0, "max": 1440.0,
            },
            "recession_minutes": {
                "type": "number", "label": "Recession", "unit": "min",
                "default": 120.0, "min": 0.0, "max": 2880.0,
            },
            "duration_hours": {
                "type": "number", "label": "Simulated duration", "unit": "h",
                "default": 6.0, "min": 0.25, "max": 72.0,
            },
            "n_manning": {
                "type": "number", "label": "Manning roughness",
                "help": "0.03 smooth channel, 0.05 typical, 0.10 dense vegetation.",
                "default": 0.05, "min": 0.01, "max": 0.2,
            },
            "rain_mm_per_hour": {
                "type": "number", "label": "Uniform rainfall", "unit": "mm/h",
                "default": 0.0, "min": 0.0, "max": 300.0,
            },
            "scale_m": {
                "type": "number", "label": "Grid resolution", "unit": "m",
                "default": 30.0, "enum": [10, 30, 60, 90],
            },
            "n_frames": {
                "type": "integer", "label": "Animation frames",
                "default": 48, "min": 2, "max": 240,
            },
            "fill_dem_pits": {
                "type": "boolean", "label": "Fill DEM depressions",
                "help": (
                    "Removes sensor artefacts that trap water and stop the flood "
                    "receding. Changes the terrain; always reported in the result."
                ),
                "default": True,
            },
        },
    },
    "fire_simulation": {
        "function": simulate_fire,
        "display_name": "Wildfire Spread Simulation (forward model)",
        "description": (
            "SIMULATED, not observed. Spreads a surface fire across real "
            "Copernicus GLO-30 terrain using Rothermel fire behaviour and "
            "Finney minimum-travel-time propagation, producing an animated "
            "burn with arrival times, flame lengths and a growth curve. "
            "Answers 'where would a fire go from here, in this fuel, under "
            "this wind?' — the question a satellite cannot answer, because "
            "the fire has not happened. For a fire that did happen, use "
            "Wildfire Burn Scar Mapping."
        ),
        "category": "Simulation (forward model)",
        "data_sources": ["GLO-30"],
        "estimated_seconds": 90,
        "output_type": "simulation",
        "color_palette": ["#FFD166", "#F4743B", "#B5192B"],
        "icon": "flame",
        "mode": "simulated",
        "accepts_params": True,
        "params_schema": {
            "scene": {
                "type": "string",
                "label": "Showcase scene",
                "help": "Preset AOI, fuel and wind. Overrides the AOI box.",
                "enum": sorted(FIRE_SCENES),
                "default": None,
            },
            "fuel_model": {
                "type": "string", "label": "Fuel model",
                "help": "Anderson (1982) standard fuel models.",
                "enum": sorted(FUEL_MODELS),
                "default": "sh5",
            },
            "wind_ms": {
                "type": "number", "label": "Midflame wind", "unit": "m/s",
                "help": (
                    "Wind AT THE FLAME, not the 10 m weather wind — typically "
                    "a third to a half of it."
                ),
                "default": 5.0, "min": 0.0, "max": 25.0,
            },
            "wind_from_bearing": {
                "type": "number", "label": "Wind from", "unit": "deg",
                "help": "Compass bearing the wind blows FROM. 270 is a westerly.",
                "default": 270.0, "min": 0.0, "max": 360.0,
            },
            "duration_hours": {
                "type": "number", "label": "Duration", "unit": "h",
                "default": 8.0, "min": 0.25, "max": 72.0,
            },
            "moisture_1h": {
                "type": "number", "label": "1-hour fuel moisture",
                "help": "Fraction, not percent: 0.06 is 6%.",
                "default": 0.06, "min": 0.01, "max": 0.5,
            },
            "moisture_10h": {
                "type": "number", "label": "10-hour fuel moisture",
                "default": 0.07, "min": 0.01, "max": 0.5,
            },
            "moisture_100h": {
                "type": "number", "label": "100-hour fuel moisture",
                "default": 0.08, "min": 0.01, "max": 0.5,
            },
            "moisture_live": {
                "type": "number", "label": "Live fuel moisture",
                "help": "1.0 is fully green; 0.3 is cured.",
                "default": 1.0, "min": 0.3, "max": 3.0,
            },
            "scale_m": {
                "type": "number", "label": "Grid resolution", "unit": "m",
                "default": 30.0, "min": 10.0, "max": 200.0,
            },
            "neighbours": {
                "type": "number", "label": "Spread directions",
                "help": (
                    "More directions, less lattice bias: 8 overestimates "
                    "off-axis travel by 8%, 16 by 2.8%, 32 by 1.3%."
                ),
                "enum": [8, 16, 32], "default": 32,
            },
            "ignition_point": {
                "type": "point", "label": "Ignition point",
                "help": "Where the fire starts. Defaults to the AOI centre.",
                "default": None,
            },
        },
    },
    "archaeology": {
        "function": detect_anomalies,
        "display_name": "Archaeology Mode (L-band anomalies)",
        "description": (
            "L-band radar (ALOS PALSAR) penetrates dry sand and forest canopy, "
            "so buried or vegetation-hidden structure can surface as texture "
            "anomalies against the natural neighbourhood pattern. Produces "
            "CANDIDATE targets for ground survey — modern tracks and field "
            "boundaries look identical from orbit."
        ),
        "category": "Research",
        "data_sources": ["PALSAR"],
        "estimated_seconds": 30,
        "output_type": "raster",
        "color_palette": ["#E8A318"],
        "icon": "landmark",
        "sar_polarization": "HV",
        "instrument_mode": "ScanSAR mosaic",
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
            # Observation vs forward model. Every entry that does not say
            # otherwise measures something a satellite actually recorded; the
            # frontend and the AI layer both key off this to keep simulated
            # output from ever being described as a detection.
            "mode": cfg.get("mode", "observed"),
            # Entries with a parameter schema take an extra `params` object;
            # the sidebar renders a form from it.
            "accepts_params": cfg.get("accepts_params", False),
            "params_schema": cfg.get("params_schema"),
        }
        for analysis_id, cfg in ANALYSIS_REGISTRY.items()
    ]
