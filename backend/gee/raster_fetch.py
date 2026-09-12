"""
Pull a co-registered raster out of Earth Engine as a NumPy array.

Every other analysis in Kairos keeps its computation server-side and brings
back a tile URL and a handful of reduced scalars. The forward solver cannot
work that way: it needs the actual elevation values in memory to integrate the
shallow-water equations over them. This module is the one place that downloads
pixels, and it is deliberately fenced in — a hard cell-count cap, a disk cache,
and a single `computePixels` call rather than a GeoTIFF export pipeline.

`ee.data.computePixels(fileFormat='NPY')` returns a structured NumPy array
directly, so there is no rasterio, no GDAL, and no new dependency.

Projection — the part that silently ruins everything
----------------------------------------------------
The solver integrates on a grid with one cell size `dx` in metres, applied in
both directions. A raster sampled on a lat/lon grid does not have that: a cell
spanning 0.00027° is about 30 m tall everywhere, but only 30·cos(latitude) m
wide — 21 m at 45° N, 15 m at 60° N. Handing such a grid to the solver stretches
the free-surface gradient in one direction and routes water at a systematically
wrong angle, over the whole domain, with nothing in the output that looks wrong.

So the raster is requested in a **metric CRS** — the UTM zone containing the
AOI's centre — and the solver receives genuinely square cells. `utm_epsg` and
`plan_grid` below are pure functions and are unit-tested without Earth Engine;
`fetch_dem` is the thin shell that actually talks to it.
"""

import hashlib
import io
import math
import os
from dataclasses import dataclass

import numpy as np

#: Copernicus GLO-30 — the same DEM `gee/flood_depth.py` already uses.
#: It is a *surface* model: canopy and buildings are included in the elevation.
#: For flood routing that is a defensible approximation (buildings genuinely do
#: block flow) but it is an approximation, and it is reported in the output.
GLO30 = "COPERNICUS/DEM/GLO30"

#: Hard ceiling on cells fetched in one request. `computePixels` caps its own
#: response size, and a demo feature has no business solving county-sized
#: domains: 1M cells at 30 m is a 30 x 30 km AOI, already generous.
MAX_CELLS = 1_000_000

#: Default ground sample distance in metres. GLO-30's native resolution.
DEFAULT_SCALE_M = 30.0

_CACHE_VERSION = 2


@dataclass
class DemTile:
    """
    An elevation array with everything needed to place it back on Earth.

    `bbox` is the lat/lon box that was *requested*. The array itself is a
    rectangle in `crs`, anchored at (`origin_easting`, `origin_northing`) —
    its north-west corner — and the two do not coincide exactly, because a
    lat/lon rectangle is not a rectangle in UTM. Over a 10 km AOI the
    disagreement is a few metres. The projected origin is carried here so a
    consumer that needs exact georeferencing has it without a second fetch,
    rather than having to assume the array fills the bbox precisely.
    """

    dem: np.ndarray          # (ny, nx) float64 metres above the ellipsoid
    dx: float                # cell size in metres, square by construction
    crs: str                 # e.g. 'EPSG:32612'
    bbox: list               # the requested [min_lon, min_lat, max_lon, max_lat]
    source: str = GLO30
    cached: bool = False
    origin_easting: float | None = None    # NW corner of the grid, in `crs`
    origin_northing: float | None = None
    void_fraction: float = 0.0             # share of cells that had no data

    @property
    def shape(self) -> tuple:
        return self.dem.shape

    def as_dict(self) -> dict:
        ny, nx = self.dem.shape
        return {
            "dem_source": self.source,
            "dem_crs": self.crs,
            "dem_scale_m": self.dx,
            "dem_shape": [ny, nx],
            "dem_min_m": float(self.dem.min()),
            "dem_max_m": float(self.dem.max()),
            "dem_cached": self.cached,
            "dem_origin_easting": self.origin_easting,
            "dem_origin_northing": self.origin_northing,
            "dem_void_fraction": round(self.void_fraction, 6),
            "dem_note": (
                "Copernicus GLO-30 is a digital *surface* model: canopy and "
                "buildings are part of the elevation, so flow is routed around "
                "structures rather than through them."
            ),
        }


def utm_epsg(lon: float, lat: float) -> str:
    """
    The EPSG code of the UTM zone containing a point.

    326xx north of the equator, 327xx south. Longitudes are wrapped into
    [-180, 180) so an AOI straddling the antimeridian still resolves.
    """
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} is outside [-90, 90].")
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    zone = int((wrapped + 180.0) / 6.0) + 1
    zone = min(max(zone, 1), 60)
    hemisphere = 326 if lat >= 0 else 327
    return f"EPSG:{hemisphere}{zone:02d}"


def bbox_extent_m(bbox: list) -> tuple:
    """
    Approximate (width, height) of a lat/lon bbox in metres.

    Used to size the request before making it. A spherical approximation is
    plenty for deciding whether an AOI is too big — the actual grid comes back
    from Earth Engine in a projected CRS, not from this.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = math.radians((min_lat + max_lat) / 2.0)
    width = (max_lon - min_lon) * 111_320.0 * math.cos(mid_lat)
    height = (max_lat - min_lat) * 110_540.0
    return abs(width), abs(height)


@dataclass
class GridPlan:
    """The raster request that will be made, decided before making it."""

    crs: str
    scale_m: float
    nx: int
    ny: int
    requested_scale_m: float
    downscaled: bool

    @property
    def cells(self) -> int:
        return self.nx * self.ny


def plan_grid(
    bbox: list,
    scale_m: float = DEFAULT_SCALE_M,
    max_cells: int = MAX_CELLS,
    allow_coarsen: bool = True,
) -> GridPlan:
    """
    Decide the CRS and grid shape for an AOI, enforcing the cell cap.

    If the AOI would exceed `max_cells` at the requested resolution, the scale
    is coarsened just enough to fit (and the plan says so) rather than silently
    truncating the area — a smaller flood over the right region beats a
    full-resolution flood over a third of it. With `allow_coarsen=False` an
    oversized AOI raises instead, which is what the API does so the user is
    told rather than quietly given something coarser than they asked for.
    """
    if scale_m <= 0:
        raise ValueError(f"scale_m must be positive; got {scale_m}.")
    if max_cells < 100:
        raise ValueError(f"max_cells must be at least 100; got {max_cells}.")

    width_m, height_m = bbox_extent_m(bbox)
    if width_m <= 0 or height_m <= 0:
        raise ValueError(f"Degenerate AOI {bbox}: it has no area.")

    centre_lon = (bbox[0] + bbox[2]) / 2.0
    centre_lat = (bbox[1] + bbox[3]) / 2.0
    crs = utm_epsg(centre_lon, centre_lat)

    scale = float(scale_m)
    cells = (width_m / scale) * (height_m / scale)
    downscaled = False
    if cells > max_cells:
        if not allow_coarsen:
            km2 = width_m * height_m / 1e6
            raise ValueError(
                f"This area ({km2:.0f} km²) needs {cells:,.0f} cells at "
                f"{scale_m:.0f} m, over the {max_cells:,} cell limit. Draw a "
                f"smaller box, or request a coarser scale (try "
                f"{math.ceil(scale * math.sqrt(cells / max_cells)):.0f} m)."
            )
        scale = scale * math.sqrt(cells / max_cells)
        downscaled = True

    nx = max(int(width_m / scale), 3)
    ny = max(int(height_m / scale), 3)
    return GridPlan(
        crs=crs,
        scale_m=scale,
        nx=nx,
        ny=ny,
        requested_scale_m=float(scale_m),
        downscaled=downscaled,
    )


def cache_key(bbox: list, plan: GridPlan, source: str) -> str:
    """A stable filename for one fetched tile."""
    payload = (
        f"v{_CACHE_VERSION}|{source}|{plan.crs}|{plan.scale_m:.4f}|"
        f"{plan.nx}x{plan.ny}|" + ",".join(f"{c:.6f}" for c in bbox)
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _cache_dir() -> str:
    return os.getenv("KAIROS_RASTER_CACHE", os.path.join("data", "raster_cache"))


def _load_cached(path: str):
    """Returns (dem, void_fraction) or None."""
    try:
        with np.load(path) as bundle:
            return bundle["dem"], float(bundle["void_fraction"])
    except Exception:
        return None


def _store_cached(path: str, dem: np.ndarray, void_fraction: float) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path, dem=dem, void_fraction=void_fraction)
    except Exception:
        pass  # A failed cache write is never worth failing a request over.


#: How far the array's own corner elevation may disagree with an independent
#: GEE sample at the same point before the array is rejected. GLO-30 is a
#: mosaic and computePixels resamples, so a few metres of genuine disagreement
#: between two different sampling paths is normal; tens or hundreds of metres,
#: or a sign flip, means the grid is misaligned or transposed, not noisy.
ORIENTATION_TOLERANCE_M = 20.0


def check_orientation(dem: np.ndarray, corner_elevations: dict) -> None:
    """
    Verify the array's four corners match independently-sampled elevations.

    This is the guard for the one failure mode in this module that does NOT
    degrade to a clear error: a wrong affine transform (a flipped axis, a
    transposed array, an off-by-one origin) still returns a full, plausible-
    looking elevation grid — it just has north and south, or east and west,
    swapped. Fed to the solver, that produces a confidently wrong, visually
    convincing animation (water flowing uphill) rather than a crash.

    `corner_elevations` is sampled by GEE's own point reducer, entirely
    independently of the affine transform this module builds by hand — so
    agreement here means two different code paths agree on where north is,
    not that one internally-consistent-but-wrong path agrees with itself.

    Args:
        dem: the fetched (ny, nx) array.
        corner_elevations: {"nw": float, "ne": float, "sw": float, "se": float},
            each an elevation sampled directly at that corner's lon/lat by GEE.

    Raises:
        ValueError: any corner disagrees by more than ORIENTATION_TOLERANCE_M,
            naming which corner(s) and by how much — enough to tell a genuine
            axis flip from ordinary resampling noise at a glance.
    """
    ny, nx = dem.shape
    array_corners = {
        "nw": dem[0, 0], "ne": dem[0, nx - 1],
        "sw": dem[ny - 1, 0], "se": dem[ny - 1, nx - 1],
    }
    mismatches = []
    for corner, expected in corner_elevations.items():
        actual = array_corners[corner]
        if not np.isfinite(expected):
            continue    # a void at the exact corner pixel; not a signal either way
        diff = abs(actual - expected)
        if diff > ORIENTATION_TOLERANCE_M:
            mismatches.append(f"{corner}: array={actual:.1f}m independent={expected:.1f}m (diff {diff:.1f}m)")

    if mismatches:
        raise ValueError(
            "DEM orientation check failed — the fetched array does not match "
            "independently-sampled elevation at its own corners, which means "
            "the grid is misaligned, flipped, or transposed rather than just "
            "noisy (tolerance is " + f"{ORIENTATION_TOLERANCE_M:.0f}m). "
            "Routing water on this grid would silently run it the wrong way. "
            "Mismatches: " + "; ".join(mismatches)
        )


def _sample_corners(image, crs: str, corners: dict) -> dict:
    """
    Independently sample `image` at four (easting, northing) points in `crs`.

    Uses ee.Geometry.Point + reduceRegion per point rather than reusing any
    machinery from the fetch path above — the whole point is a second,
    unrelated way of answering "what elevation is here?" to check the first.
    `image` must be an ee.Image; ee is not imported at module level (see the
    module docstring), so the caller — already inside the lazy `import ee`
    block in `fetch_dem` — passes it in rather than this helper importing it
    again.
    """
    import ee  # noqa: PLC0415 — mirrors fetch_dem's lazy import; see docstring.

    result = {}
    for name, (x, y) in corners.items():
        point = ee.Geometry.Point([x, y], crs)
        value = image.reduceRegion(
            reducer=ee.Reducer.first(), geometry=point, scale=30,
        ).get("DEM")
        got = value.getInfo()
        result[name] = float(got) if got is not None else float("nan")
    return result


def fetch_dem(
    bbox: list,
    scale_m: float = DEFAULT_SCALE_M,
    max_cells: int = MAX_CELLS,
    allow_coarsen: bool = True,
    use_cache: bool = True,
) -> DemTile:
    """
    Fetch a Copernicus GLO-30 elevation array for a bbox, in a metric CRS.

    Earth Engine is imported lazily so this module (and everything that
    imports it) stays importable — and unit-testable — without credentials.

    Raises:
        ValueError: AOI too large, degenerate, or no elevation data returned.
    """
    plan = plan_grid(bbox, scale_m, max_cells, allow_coarsen=allow_coarsen)

    path = os.path.join(_cache_dir(), f"glo30-{cache_key(bbox, plan, GLO30)}.npz")
    if use_cache:
        hit = _load_cached(path)
        if hit is not None:
            dem, void_fraction = hit
            return DemTile(
                dem=dem, dx=plan.scale_m, crs=plan.crs, bbox=list(bbox),
                cached=True, void_fraction=void_fraction,
            )

    import ee  # noqa: PLC0415 — deliberately lazy; see docstring.

    from gee import common  # noqa: PLC0415 — pulls in ee at import time.

    common.bbox_geometry(bbox)   # waits for the background GEE init handshake

    # Deliberately NOT clipped to the AOI. The requested grid is a rectangle in
    # UTM while the bbox is a rectangle in lat/lon, so the two do not coincide
    # exactly; clipping would mask the sliver of the grid that falls outside
    # the bbox, and those masked cells would then be void-filled into a fake
    # low wall that ponds water along the edge.
    image = ee.ImageCollection(GLO30).select("DEM").mosaic()

    # computePixels states the grid in the target CRS. The affine is anchored
    # at the AOI's projected south-west corner, and `translateY` is the NORTH
    # edge with a negative scaleY, so row 0 of the returned array is the
    # northernmost row — the orientation `solver.grid` documents.
    corner = ee.Geometry.Point([bbox[0], bbox[1]]).transform(plan.crs, 1)
    x0, y0 = corner.coordinates().getInfo()      # one round trip, not two
    top = float(y0) + plan.ny * plan.scale_m

    try:
        encoded = ee.data.computePixels(
            {
                "expression": image,
                "fileFormat": "NPY",
                "bandIds": ["DEM"],
                "grid": {
                    "dimensions": {"width": plan.nx, "height": plan.ny},
                    "affineTransform": {
                        "scaleX": plan.scale_m,
                        "shearX": 0.0,
                        "translateX": float(x0),
                        "shearY": 0.0,
                        "scaleY": -plan.scale_m,
                        "translateY": top,
                    },
                    "crsCode": plan.crs,
                },
            }
        )
    except Exception as exc:
        raise ValueError(
            f"Earth Engine could not return elevation pixels for this area "
            f"({plan.nx}x{plan.ny} at {plan.scale_m:.0f} m in {plan.crs}): {exc}"
        ) from exc

    # fileFormat 'NPY' hands back the bytes of a .npy file holding a structured
    # array with one field per requested band — not an ndarray directly.
    structured = np.load(io.BytesIO(encoded), allow_pickle=False)
    dem = np.asarray(structured["DEM"], dtype=np.float64)
    if dem.size == 0:
        raise ValueError(f"No GLO-30 elevation data covers {bbox}.")

    # GLO-30 carries voids over open water. Filling them with the lowest real
    # elevation in the domain is the honest choice for a coastal AOI — sea
    # level is the lowest surface present — and keeps the free-surface
    # gradient finite, since one NaN poisons the entire solve. The fraction
    # filled is reported so a domain that is mostly void is visible rather
    # than quietly modelled.
    finite_mask = np.isfinite(dem)
    void_fraction = float((~finite_mask).mean())
    if void_fraction > 0.0:
        if not finite_mask.any():
            raise ValueError(
                f"GLO-30 returned no valid elevations for {bbox} — the AOI is "
                f"probably entirely over water."
            )
        dem = np.where(finite_mask, dem, float(dem[finite_mask].min()))

    # Orientation guard (see module note on projection, and check_orientation's
    # own docstring): sample the four corners of the exact grid just fetched,
    # independently of the affine transform above, and confirm they agree.
    # A wrong axis flip or transposition would otherwise return a full,
    # plausible-looking grid with north and south — or east and west — swapped,
    # which is the one failure mode here that does not fail loudly on its own.
    half = plan.scale_m / 2.0   # sample pixel centres, not their corners
    corner_points = {
        "nw": (x0 + half, top - half),
        "ne": (x0 + plan.nx * plan.scale_m - half, top - half),
        "sw": (x0 + half, top - plan.ny * plan.scale_m + half),
        "se": (x0 + plan.nx * plan.scale_m - half, top - plan.ny * plan.scale_m + half),
    }
    independent = _sample_corners(image, plan.crs, corner_points)
    check_orientation(dem, independent)

    if use_cache:
        _store_cached(path, dem, void_fraction)

    return DemTile(
        dem=dem,
        dx=plan.scale_m,
        crs=plan.crs,
        bbox=list(bbox),
        origin_easting=float(x0),
        origin_northing=top,
        void_fraction=void_fraction,
    )
