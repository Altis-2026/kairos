"""
Curated showcase scenes for the flood simulator.

Two jobs. First, a demo that depends on the user drawing a good box and
guessing a discharge is a demo that fails in front of people; these are AOIs
picked because their terrain routes water legibly. Second, once the DEM for a
scene is cached, the whole simulation runs with no Earth Engine round-trip at
all, so a showcase works on a bad conference network.

Every hydrograph here is **illustrative**. None is derived from a gauge record
or a rainfall observation — they are shaped to resemble a flash-flood rise and
recession at a plausible magnitude for the catchment, and that is all they
claim. The `disclosure` string on each scene travels with the result all the
way to the UI, because a synthetic hydrograph over real terrain looks exactly
as convincing as a real one and the difference has to be stated, not implied.

Bounding boxes are approximate: they frame the reach, they are not surveyed
catchment boundaries.
"""

from dataclasses import dataclass, field

ILLUSTRATIVE = (
    "Illustrative hydrograph — a plausible flash-flood shape for this "
    "catchment, not a gauge record or a forecast. The terrain is real; the "
    "water is modelled."
)


@dataclass(frozen=True)
class Scene:
    """One showcase simulation, fully specified."""

    id: str
    name: str
    region: str
    bbox: tuple                    # (min_lon, min_lat, max_lon, max_lat)
    summary: str
    peak_discharge_m3s: float
    rise_minutes: float
    peak_minutes: float
    recession_minutes: float
    duration_hours: float
    n_manning: float = 0.05
    scale_m: float = 30.0
    dt_max: float = 5.0
    rain_mm_per_hour: float = 0.0
    disclosure: str = ILLUSTRATIVE
    tags: tuple = field(default_factory=tuple)

    def hydrograph(self) -> list:
        """Piecewise-linear [(t_seconds, m³/s), ...] for this scene."""
        rise = self.rise_minutes * 60.0
        plateau = rise + self.peak_minutes * 60.0
        end = plateau + self.recession_minutes * 60.0
        return [
            (0.0, 0.0),
            (rise, self.peak_discharge_m3s),
            (plateau, self.peak_discharge_m3s),
            (end, 0.0),
        ]

    def duration_s(self) -> float:
        return self.duration_hours * 3600.0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "bbox": list(self.bbox),
            "summary": self.summary,
            "peak_discharge_m3s": self.peak_discharge_m3s,
            "rise_minutes": self.rise_minutes,
            "peak_minutes": self.peak_minutes,
            "recession_minutes": self.recession_minutes,
            "duration_hours": self.duration_hours,
            "n_manning": self.n_manning,
            "scale_m": self.scale_m,
            "dt_max": self.dt_max,
            "rain_mm_per_hour": self.rain_mm_per_hour,
            "disclosure": self.disclosure,
            "tags": list(self.tags),
            "mode": "simulated",
        }


SCENES = {
    s.id: s
    for s in (
        Scene(
            id="bright_angel_canyon",
            name="Bright Angel Creek, Grand Canyon",
            region="Arizona, USA",
            bbox=(-112.135, 36.060, -112.050, 36.130),
            summary=(
                "A slot canyon draining to the Colorado. Extreme relief over a "
                "short reach, so the wave is fast, deep and tightly confined — "
                "the clearest demonstration that the solver routes water by "
                "terrain rather than painting a flat plane."
            ),
            peak_discharge_m3s=220.0,
            rise_minutes=25.0,
            peak_minutes=20.0,
            recession_minutes=90.0,
            duration_hours=5.0,
            n_manning=0.045,          # bedrock and boulder channel
            tags=("canyon", "flash flood", "high relief"),
        ),
        Scene(
            id="rio_ruidoso_burn",
            name="Rio Ruidoso below the burn scar",
            region="New Mexico, USA",
            bbox=(-105.715, 33.300, -105.605, 33.380),
            summary=(
                "A post-fire catchment, where lost vegetation and hydrophobic "
                "soil turn ordinary rain into a flash flood. Kairos already "
                "maps burn scars from Sentinel-1; this is the same ground as a "
                "forward model, and the natural first place to couple the two."
            ),
            peak_discharge_m3s=160.0,
            rise_minutes=15.0,        # post-fire catchments respond fast
            peak_minutes=15.0,
            recession_minutes=75.0,
            duration_hours=4.0,
            n_manning=0.035,          # burned ground is smooth; runoff is quick
            tags=("post-fire", "flash flood", "burn scar"),
        ),
        Scene(
            id="guadalupe_hill_country",
            name="Guadalupe River, Texas Hill Country",
            region="Texas, USA",
            bbox=(-99.400, 30.020, -99.280, 30.105),
            summary=(
                "Thin soil over limestone in a river valley that rises far "
                "faster than people expect. A wide floodplain next to a "
                "confined channel makes the depth contrast easy to read."
            ),
            peak_discharge_m3s=900.0,
            rise_minutes=45.0,
            peak_minutes=40.0,
            recession_minutes=180.0,
            duration_hours=8.0,
            n_manning=0.055,
            scale_m=40.0,
            tags=("river", "flash flood", "floodplain"),
        ),
        Scene(
            id="feather_river_oroville",
            name="Feather River below Oroville",
            region="California, USA",
            bbox=(-121.545, 39.495, -121.425, 39.580),
            summary=(
                "A high-magnitude release into a confined river below a major "
                "dam — the scenario satellites cannot answer, because it is "
                "about water that has not arrived yet."
            ),
            peak_discharge_m3s=2200.0,
            rise_minutes=30.0,
            peak_minutes=120.0,
            recession_minutes=240.0,
            duration_hours=12.0,
            n_manning=0.05,
            scale_m=45.0,
            tags=("dam release", "river", "scenario"),
        ),
        Scene(
            id="jamuna_sirajganj",
            name="Jamuna River near Sirajganj",
            region="Bangladesh",
            bbox=(89.620, 24.380, 89.780, 24.520),
            summary=(
                "A braided delta reach on very low relief — the hardest case "
                "for a terrain-driven solver and the one that matters most for "
                "exposure, since a few centimetres of gradient decide which "
                "side of the channel floods."
            ),
            peak_discharge_m3s=4500.0,
            rise_minutes=180.0,       # monsoon flooding builds over hours
            peak_minutes=240.0,
            recession_minutes=480.0,
            duration_hours=18.0,
            n_manning=0.06,           # vegetated, agricultural floodplain
            scale_m=60.0,
            dt_max=15.0,              # low relief; the CFL step is generous
            tags=("delta", "monsoon", "low relief"),
        ),
    )
}

SCENE_IDS = tuple(SCENES)


def get_scene(scene_id: str) -> Scene:
    """Look up a showcase scene, failing with the list of what exists."""
    try:
        return SCENES[scene_id]
    except KeyError:
        raise ValueError(
            f"Unknown scene '{scene_id}'. Available: {list(SCENE_IDS)}"
        ) from None


def scenes_as_json() -> list:
    """Serializable catalogue for GET /simulate/scenes."""
    return [scene.as_dict() for scene in SCENES.values()]
