"""
Curated showcase scenes for the wildfire simulator.

Same two jobs as the flood presets: a demo that needs the user to draw a good
box, pick a fuel model and guess a wind is a demo that fails in front of
people, and once a scene's DEM is cached the whole thing runs with no Earth
Engine round-trip at all.

Every scene here is **a scenario, not a reconstruction**. The terrain is real
and the locations are places that have burned, but the fuel model, wind,
moisture and ignition point are choices — plausible ones for the landscape and
season, and nothing more. None of these reproduces the actual fire that
happened at that place, which depended on fuel continuity, spotting, crowning,
wind shifts and suppression that this model does not represent. That
distinction is not pedantry: a simulated burn over a real, named place looks
exactly as convincing as a reconstruction, and people will read it as one
unless told otherwise. The `disclosure` string travels with the result all the
way to the UI for that reason.

Bounding boxes frame the terrain of interest; they are not fire perimeters.
"""

from dataclasses import dataclass, field

SCENARIO = (
    "Illustrative scenario — plausible fuel, wind and ignition for this "
    "landscape, not a reconstruction of any actual fire. The terrain is "
    "real; the fire is modelled."
)


@dataclass(frozen=True)
class FireScene:
    """One showcase fire, fully specified."""

    id: str
    name: str
    region: str
    bbox: tuple                      # (min_lon, min_lat, max_lon, max_lat)
    summary: str
    fuel_model: str
    wind_ms: float                   # midflame, already reduced from 10 m
    wind_from_bearing: float         # degrees the wind blows FROM
    duration_hours: float
    ignition_point: tuple            # (lon, lat)
    moisture_1h: float = 0.05
    moisture_10h: float = 0.06
    moisture_100h: float = 0.08
    moisture_live: float = 0.70
    scale_m: float = 30.0
    disclosure: str = SCENARIO
    tags: tuple = field(default_factory=tuple)


SCENES = {
    "malibu_chaparral": FireScene(
        id="malibu_chaparral",
        name="Santa Monica Mountains, California",
        region="California, USA",
        bbox=(-118.82, 34.06, -118.66, 34.14),
        summary=(
            "Mature chaparral on steep coastal canyons. A dry offshore wind "
            "drives fire downslope toward the coast — the pattern behind "
            "southern California's most destructive fires, and the one that "
            "defeats the usual intuition that fire runs uphill."
        ),
        fuel_model="sh4",
        wind_ms=6.5,
        wind_from_bearing=30.0,          # Santa Ana: offshore, from the NNE
        duration_hours=8.0,
        ignition_point=(-118.78, 34.125),
        moisture_1h=0.03,
        moisture_10h=0.04,
        moisture_100h=0.06,
        moisture_live=0.60,
        tags=("chaparral", "wind-driven", "santa-ana"),
    ),
    "sierra_timber": FireScene(
        id="sierra_timber",
        name="Sierra Nevada Foothills, California",
        region="California, USA",
        bbox=(-121.70, 39.72, -121.52, 39.84),
        summary=(
            "Timber with a heavy understory in steep drainages above the "
            "Feather River. Slope-driven runs up the canyon walls dominate, "
            "and the terrain concentrates the fire into chimneys."
        ),
        fuel_model="tu10",
        wind_ms=4.0,
        wind_from_bearing=45.0,
        duration_hours=12.0,
        ignition_point=(-121.66, 39.755),
        moisture_live=0.80,
        tags=("timber", "slope-driven", "canyon"),
    ),
    "front_range_grass": FireScene(
        id="front_range_grass",
        name="Colorado Front Range Grassland",
        region="Colorado, USA",
        bbox=(-105.24, 39.94, -105.08, 40.03),
        summary=(
            "Cured short grass on rolling ground under a strong downslope "
            "windstorm. Grass fires carry almost no fuel but move faster than "
            "anything else in the model — the reason a grassland fire can "
            "cross open country before anyone can respond."
        ),
        fuel_model="gr1",
        wind_ms=11.0,
        wind_from_bearing=270.0,
        duration_hours=5.0,
        ignition_point=(-105.20, 39.985),
        moisture_1h=0.04,
        moisture_10h=0.05,
        moisture_100h=0.06,
        moisture_live=1.00,
        scale_m=30.0,
        tags=("grass", "wind-driven", "fast"),
    ),
    "pedrogao_portugal": FireScene(
        id="pedrogao_portugal",
        name="Pedrógão Grande, Central Portugal",
        region="Leiria, Portugal",
        bbox=(-8.30, 39.90, -8.14, 40.00),
        summary=(
            "Dense eucalyptus and pine on dissected hills. Steep, narrow "
            "valleys with fuel continuous from valley floor to ridgeline — "
            "terrain where a fire's spread is governed as much by the shape "
            "of the ground as by the wind over it."
        ),
        fuel_model="sh7",
        wind_ms=5.0,
        wind_from_bearing=200.0,
        duration_hours=10.0,
        ignition_point=(-8.26, 39.935),
        moisture_1h=0.04,
        moisture_live=0.65,
        tags=("mediterranean", "steep", "plantation"),
    ),
    "blue_mountains_nsw": FireScene(
        id="blue_mountains_nsw",
        name="Blue Mountains, New South Wales",
        region="New South Wales, Australia",
        bbox=(150.28, -33.74, 150.46, -33.62),
        summary=(
            "Dry sclerophyll forest above sandstone escarpments. Deep gorges "
            "and long unbroken slopes let a fire run for hours once it is "
            "established below the cliff line."
        ),
        fuel_model="sh6",
        wind_ms=7.5,
        wind_from_bearing=315.0,
        duration_hours=14.0,
        ignition_point=(150.32, -33.715),
        moisture_1h=0.04,
        moisture_10h=0.05,
        moisture_live=0.75,
        scale_m=30.0,
        tags=("eucalypt", "escarpment", "long-run"),
    ),
    "rhodes_greece": FireScene(
        id="rhodes_greece",
        name="Rhodes Interior, Greece",
        region="South Aegean, Greece",
        bbox=(27.90, 36.14, 28.06, 36.26),
        summary=(
            "Pine and maquis over the island's interior ridges in high "
            "summer. A moderate meltemi wind across complex terrain spreads "
            "the fire on several fronts at once."
        ),
        fuel_model="sh5",
        wind_ms=6.0,
        wind_from_bearing=340.0,
        duration_hours=10.0,
        ignition_point=(27.95, 36.235),
        moisture_1h=0.03,
        moisture_live=0.55,
        tags=("maquis", "island", "summer"),
    ),
}


def get_scene(scene_id: str) -> FireScene:
    """Look up a scene, failing with the list of valid ids."""
    try:
        return SCENES[scene_id]
    except KeyError:
        raise ValueError(
            f"Unknown fire scene {scene_id!r}. Available: {sorted(SCENES)}"
        ) from None


def scenes_as_json() -> list:
    """The scene catalogue, for the API and the UI picker."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "region": s.region,
            "bbox": list(s.bbox),
            "summary": s.summary,
            "fuel_model": s.fuel_model,
            "wind_ms": s.wind_ms,
            "wind_from_bearing": s.wind_from_bearing,
            "duration_hours": s.duration_hours,
            "ignition_point": list(s.ignition_point),
            "scale_m": s.scale_m,
            "disclosure": s.disclosure,
            "tags": list(s.tags),
            # Carried on the scene itself, not only on the result. A scene
            # list is browsed before anything is run, so this is the first
            # place a user can be told the event is modelled.
            "mode": "simulated",
        }
        for s in SCENES.values()
    ]
